"""Generic clickable placement board shared by the pizza-topping builder
and the cupcake-plate builder in party_ui.py.

Shows a row of inventory item pngs (one is "active"), and a row of base
pngs (pizza bases or plates, one per kid). Clicking an inventory png makes
it active; clicking a base places one unit of the active item onto it, at
a random position inside the base art's own circular shape (so pieces can
overlap, like real toppings piled on a pizza), decrementing a working
inventory copy; clicking an already-placed item on a base removes it,
incrementing the working copy back. The working inventory/placements are
plain Python state on the PlacementBoard instance -- callers can destroy
and recreate the Tk frames it renders into at will (via render()) without
losing that state.

Because pieces can overlap, whichever item is currently active is drawn
on top of (and with a highlighted border over) every other piece already
on a base, so it's both visually identifiable and gets click priority for
removal even where it overlaps other toppings.

The base grid (how many bases per row, and how big each base renders) is
derived from base_count so it stays reasonable whether there are 2 kids or
50: more bases per row (roughly a square grid) and a smaller base size as
base_count grows, rather than a fixed-width column count that would just
get taller and taller.

Usage:

    board = PlacementBoard(
        base_image_path="partyimages/pizza.png",
        items=[("pineapple", "shopimages/pineapple.png"), ...],
        base_count=num_kids,
        initial_inventory={"pineapple": 4, ...},
        show_item_switcher=True,
        placement_circle_fraction=0.78)
    board.render(switcher_frame, bases_frame)
"""

import random
import tkinter as tk

from PIL import Image, ImageTk

BG = "#fdf6e3"
TEXT = "#3b2f1e"
ITEM_BORDER = "#d9c9a3"
ACTIVE_BORDER = "#3aa655"
ACTIVE_BG = "#b3f5e6"
BASE_BORDER = "#d9c9a3"

ITEM_PX = 44
ITEM_ACTIVE_PX = 60
BASE_PX = 180
BASE_PX_MIN = 60
PLACED_PX = 20

# The whole board of bases is kept within roughly this width regardless of
# base_count, by shrinking each base as more of them need to fit per row.
BOARD_MAX_WIDTH = 1400
BASE_GRID_PAD = 20  # matches the .grid(padx=10) used per base in _render_bases
BASE_COLS_MAX = 4  # a row holds up to this many bases before wrapping to
                    # another row (the middle area scrolls if that still
                    # doesn't fit everything -- see party_ui.py's _middle_canvas)


class PlacementBoard:
    def __init__(self, base_image_path, items, base_count, initial_inventory,
                 show_item_switcher=True, base_px=BASE_PX,
                 placement_circle_fraction=1.0, max_board_width=BOARD_MAX_WIDTH):
        """placement_circle_fraction is the diameter, as a fraction of the
        (possibly shrunk) base size, of the circular area placed items are
        confined to -- e.g. for a base png whose art is a circle inscribed
        in its square canvas, passing that circle's own diameter fraction
        (with a little margin for the icon's own footprint) keeps every
        placed item's icon on the crust instead of spilling into the
        transparent corners of the square image. 1.0 (the default) treats
        the whole square as safe, matching a base image with no inset.

        max_board_width caps how wide the whole row of bases is allowed to
        get (each base shrinks to fit) -- pass a tighter value than the
        default when the board shares horizontal space with something else
        (e.g. party_ui.py's checklist panel beside it), or that neighbor
        can get pushed outside the visible window instead of the board
        simply wrapping to more rows.
        """
        self.items = items  # list of (name, image_path)
        self.base_count = base_count
        self.inventory = dict(initial_inventory)
        self.active_item = items[0][0]
        self.show_item_switcher = show_item_switcher
        self.placements = [[] for _ in range(base_count)]
        self.placement_circle_fraction = placement_circle_fraction

        self._base_cols = max(1, min(BASE_COLS_MAX, base_count))
        fitted_px = (max_board_width // self._base_cols) - BASE_GRID_PAD
        self.base_px = max(BASE_PX_MIN, min(base_px, fitted_px))

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
        base_img.thumbnail((self.base_px, self.base_px), Image.LANCZOS)
        self._base_icon = ImageTk.PhotoImage(base_img)

    def _random_placement_position(self):
        cx = cy = self.base_px / 2
        max_r = max(0.0, (self.base_px * self.placement_circle_fraction / 2)
                    - (PLACED_PX / 2))
        for _ in range(30):
            dx = random.uniform(-max_r, max_r)
            dy = random.uniform(-max_r, max_r)
            if dx * dx + dy * dy <= max_r * max_r:
                return cx + dx - PLACED_PX / 2, cy + dy - PLACED_PX / 2
        return cx - PLACED_PX / 2, cy - PLACED_PX / 2

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
            r, c = divmod(b, self._base_cols)
            base_lbl = tk.Label(self._bases_parent, image=self._base_icon, bg=BG,
                                highlightbackground=BASE_BORDER, highlightthickness=2,
                                cursor="hand2")
            base_lbl.grid(row=r, column=c, padx=10, pady=10)
            base_lbl.bind("<Button-1>", lambda e, bb=b: self._click_base(bb))

            active_count = sum(1 for entry in self.placements[b]
                              if entry["name"] == self.active_item)
            count_lbl = tk.Label(base_lbl, text=str(active_count), bg=ACTIVE_BG, fg=TEXT,
                                 font=("Helvetica", 11, "bold"), padx=3, pady=1)
            count_lbl.place(x=2, y=2)

            # Render the active ingredient's pieces last (on top, both
            # visually and for click priority) so they stand out and can
            # still be clicked to remove even where they overlap others.
            indexed = sorted(enumerate(self.placements[b]),
                             key=lambda pair: pair[1]["name"] == self.active_item)

            for i, entry in indexed:
                name = entry["name"]
                is_active = name == self.active_item
                placed_lbl = tk.Label(base_lbl, image=self._item_icons_small[name],
                                      bg=ACTIVE_BG if is_active else BG,
                                      highlightbackground=ACTIVE_BORDER if is_active else BG,
                                      highlightthickness=2 if is_active else 0,
                                      cursor="hand2", bd=0, padx=0, pady=0)
                placed_lbl.place(x=entry["x"], y=entry["y"])
                placed_lbl.bind("<Button-1>",
                                lambda e, bb=b, ii=i: self._click_placed(bb, ii))

    # ------------------------------------------------------------- input
    def _set_active(self, name):
        self.active_item = name
        self.render(self._switcher_parent, self._bases_parent)

    def _click_base(self, base_idx):
        if self.inventory[self.active_item] > 0:
            x, y = self._random_placement_position()
            self.placements[base_idx].append({"name": self.active_item, "x": x, "y": y})
            self.inventory[self.active_item] -= 1
            self.render(self._switcher_parent, self._bases_parent)

    def _click_placed(self, base_idx, pos):
        name = self.placements[base_idx].pop(pos)["name"]
        self.inventory[name] += 1
        self.render(self._switcher_parent, self._bases_parent)

    def reset(self):
        """Return every placed item on every base back to inventory."""
        for base_idx in range(self.base_count):
            for entry in self.placements[base_idx]:
                self.inventory[entry["name"]] += 1
            self.placements[base_idx] = []
