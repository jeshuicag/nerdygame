"""Generic clickable placement board shared by the pizza-topping builder
and the cupcake-plate builder in party_ui.py.

Shows a row of inventory item pngs (one is "active"), and a row of base
pngs (pizza bases or plates, one per kid). Clicking an inventory png makes
it active; clicking a base places one unit of the active item onto it,
decrementing a working inventory copy; clicking an already-placed item on
a base removes it, incrementing the working copy back. The working
inventory/placements are plain Python state on the PlacementBoard
instance -- callers can destroy and recreate the Tk frames it renders
into at will (via render()) without losing that state.

Usage:

    board = PlacementBoard(
        base_image_path="partyimages/pizza.png",
        items=[("pineapple", "shopimages/pineapple.png"), ...],
        base_count=num_kids,
        initial_inventory={"pineapple": 4, ...},
        show_item_switcher=True)
    board.render(switcher_frame, bases_frame)
"""

import tkinter as tk

from PIL import Image, ImageTk

BG = "#fdf6e3"
TEXT = "#3b2f1e"
ITEM_BORDER = "#d9c9a3"
ACTIVE_BORDER = "#3aa655"
ACTIVE_BG = "#e3f5e6"
BASE_BORDER = "#d9c9a3"

ITEM_PX = 44
ITEM_ACTIVE_PX = 60
BASE_PX = 110
PLACED_PX = 26
BASE_COLS = 4


class PlacementBoard:
    def __init__(self, base_image_path, items, base_count, initial_inventory,
                 show_item_switcher=True):
        self.items = items  # list of (name, image_path)
        self.base_count = base_count
        self.inventory = dict(initial_inventory)
        self.active_item = items[0][0]
        self.show_item_switcher = show_item_switcher
        self.placements = [[] for _ in range(base_count)]

        self._switcher_parent = None
        self._bases_parent = None
        self._load_images(base_image_path)

    # ------------------------------------------------------------- images
    def _load_images(self, base_image_path):
        self._item_icons = {}
        self._item_icons_active = {}
        self._item_icons_small = {}
        for name, path in self.items:
            pil_img = Image.open(path).convert("RGBA")

            small = pil_img.copy()
            small.thumbnail((ITEM_PX, ITEM_PX), Image.LANCZOS)
            self._item_icons[name] = ImageTk.PhotoImage(small)

            active = pil_img.copy()
            active.thumbnail((ITEM_ACTIVE_PX, ITEM_ACTIVE_PX), Image.LANCZOS)
            self._item_icons_active[name] = ImageTk.PhotoImage(active)

            placed = pil_img.copy()
            placed.thumbnail((PLACED_PX, PLACED_PX), Image.LANCZOS)
            self._item_icons_small[name] = ImageTk.PhotoImage(placed)

        base_img = Image.open(base_image_path).convert("RGBA")
        base_img.thumbnail((BASE_PX, BASE_PX), Image.LANCZOS)
        self._base_icon = ImageTk.PhotoImage(base_img)

    # ------------------------------------------------------------ render
    def render(self, switcher_parent, bases_parent):
        self._switcher_parent = switcher_parent
        self._bases_parent = bases_parent
        self._render_switcher()
        self._render_bases()

    def _render_switcher(self):
        for w in self._switcher_parent.winfo_children():
            w.destroy()
        if not self.show_item_switcher:
            return
        for name, _ in self.items:
            is_active = name == self.active_item
            icon = self._item_icons_active[name] if is_active else self._item_icons[name]
            lbl = tk.Label(self._switcher_parent, image=icon,
                           bg=ACTIVE_BG if is_active else BG,
                           highlightbackground=ACTIVE_BORDER if is_active else ITEM_BORDER,
                           highlightthickness=3, cursor="hand2")
            lbl.pack(side="left", padx=8)
            lbl.bind("<Button-1>", lambda e, n=name: self._set_active(n))

            count_lbl = tk.Label(self._switcher_parent, text=str(self.inventory[name]),
                                 bg=BG, fg=TEXT, font=("Helvetica", 14, "bold"))
            count_lbl.pack(side="left", padx=(0, 12))

    def _render_bases(self):
        for w in self._bases_parent.winfo_children():
            w.destroy()
        for b in range(self.base_count):
            r, c = divmod(b, BASE_COLS)
            base_lbl = tk.Label(self._bases_parent, image=self._base_icon, bg=BG,
                                highlightbackground=BASE_BORDER, highlightthickness=2,
                                cursor="hand2")
            base_lbl.grid(row=r, column=c, padx=10, pady=10)
            base_lbl.bind("<Button-1>", lambda e, bb=b: self._click_base(bb))

            for i, name in enumerate(self.placements[b]):
                row, col = divmod(i, 3)
                placed_lbl = tk.Label(base_lbl, image=self._item_icons_small[name], bg=BG,
                                      cursor="hand2")
                placed_lbl.place(x=6 + col * (PLACED_PX + 2), y=6 + row * (PLACED_PX + 2))
                placed_lbl.bind("<Button-1>",
                                lambda e, bb=b, ii=i: self._click_placed(bb, ii))

    # ------------------------------------------------------------- input
    def _set_active(self, name):
        self.active_item = name
        self.render(self._switcher_parent, self._bases_parent)

    def _click_base(self, base_idx):
        if self.inventory[self.active_item] > 0:
            self.placements[base_idx].append(self.active_item)
            self.inventory[self.active_item] -= 1
            self.render(self._switcher_parent, self._bases_parent)

    def _click_placed(self, base_idx, pos):
        name = self.placements[base_idx].pop(pos)
        self.inventory[name] += 1
        self.render(self._switcher_parent, self._bases_parent)
