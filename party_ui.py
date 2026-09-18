"""Front end for the K-5 birthday-party pizza/cupcake math game.

A single Tkinter window (reused across rounds, matching coin_ui.py and
grocery_ui.py) with a server speech bubble at top, a counter with the
server standing behind it at the bottom, and a middle zone that shows
either a plain checklist/shopping-list/number-answer widget, or -- once
allow_pizza_visual/allow_cupcake_visual is enabled -- a full clickable
pizza/plate placement visual (see placement_board.py) alongside that same
answer widget.

Usage from bdayparty.py:

    from party_ui import PartyUI
    ui = PartyUI(image_dir="partyimages", toppings_dir="shopimages")
    ui.server(text, tpk, toppings)
    enough = ui.askEnough(num_kids, tpk, t_inv, mistakes, toppings, allow_pizza_visual)
    added = ui.prompt(kids, tpk, t_inv, mistakes, warnings, toppings, allow_pizza_visual)
    answer = ui.quest(allow_cupcake_visual, num_kids, num_cakes)
"""

import os
import tkinter as tk

from PIL import Image, ImageTk

from placement_board import PlacementBoard
from shared_root import get_shared_root

BG = "#fdf6e3"
TEXT = "#3b2f1e"
BUBBLE_BG = "#ffffff"
BUBBLE_BORDER = "#3b2f1e"
LOCKED_BG = "#e8e2cf"
LOCKED_FG = "#9c8f6e"
BTN_BG = "#ffd27f"
BTN_ACTIVE = "#ffbe4d"

TOPPING_ICON_PX = 36
CHECKLIST_ICON_PX = 56
SERVER_MAX_H = 450
COUNTER_OVERLAP_FRACTION = 1  # counter height, as a fraction of server height
COUNTER_Y_SHIFT_FRACTION = 0.4  # extra drop below flush-bottom, as a
                                  # fraction of server height. The counter's
                                  # own top edge (in canvas coordinates) ends
                                  # up at server_h * (1 + shift - overlap) --
                                  # these two values are set together so that
                                  # edge stays put (currently 0.65 of the
                                  # server's height down) while overlap alone
                                  # controls how tall/wide the counter renders.
COUNTER_MAX_W_DIM = 500
SERVER_MAX_H_DIM = 130
DIM_ALPHA = 90  # out of 255
CHECKLIST_GRID_COLS = 3

# The pizza base art is a circle inscribed in its square canvas (its
# diameter measures ~81% of the canvas); the plate art is a circle that
# nearly fills its canvas edge-to-edge (~97%). Toppings/cupcakes placed on
# each are confined (with a little margin for the icon's own footprint) to
# that circle so they land on the crust/plate, never in the transparent
# corners of the square image -- see PlacementBoard.placement_circle_fraction.
PIZZA_BASE_PX = 366
PIZZA_CIRCLE_FRACTION = 0.78
CUPCAKE_CIRCLE_FRACTION = 0.92

# Tighter than PlacementBoard's own default max board width -- the pizza and
# cupcake boards render beside left_panel_frame/right_panel_frame (the
# Reset button, and for pizza the checklist/shopping-list + Submit button),
# so the board itself needs to leave room for those instead of claiming
# (up to) the full available width and pushing them outside the window.
BOARD_MAX_WIDTH_SHARED = 850


class PartyUI:
    def __init__(self, image_dir="partyimages", toppings_dir="shopimages"):
        self.image_dir = image_dir
        self.toppings_dir = toppings_dir

        self.root = tk.Toplevel(get_shared_root())
        self.root.title("Birthday Party")
        self.root.configure(bg=BG)
        # Not calling resizable(False, False) here: on some platforms it
        # locks the window's max size to whatever tiny size it has at the
        # moment it's called -- since there's no content yet, that would
        # cap every later _fit_to_screen() geometry() call to that tiny
        # size. Applied instead at the end of _fit_to_screen, once the
        # window is already sized correctly.
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._closed = False
        self._shown = False
        self._done = tk.IntVar(value=0)
        self._dimmed = False  # tracks which backdrop image is showing --
                              # see _set_backdrop_dim/_fit_to_screen

        self._topping_icons = {}
        self._pizza_board = None
        self._cupcake_board = None
        self._checklist_state = {}
        self._shoplist_state = {}
        self._num_kids = None

        self._load_backdrop_images()
        self._build()
        self.root.withdraw()

    # ------------------------------------------------------------- images
    def _load_backdrop_images(self):
        counter = Image.open(os.path.join(self.image_dir, "counter.png")).convert("RGBA")
        server = Image.open(os.path.join(self.image_dir, "server.png")).convert("RGBA")

        server_full = server.copy()
        server_full.thumbnail((10_000, SERVER_MAX_H), Image.LANCZOS)
        self._server_w = server_full.width  # middle_frame sits just right of this

        # Counter height is derived from the server's actual rendered height
        # so the overlap fraction holds regardless of SERVER_MAX_H.
        counter_target_h = round(server_full.height * COUNTER_OVERLAP_FRACTION)
        counter_full = counter.copy()
        counter_full.thumbnail((10_000, counter_target_h), Image.LANCZOS)

        counter_dim = counter.copy()
        counter_dim.thumbnail((COUNTER_MAX_W_DIM, 10_000), Image.LANCZOS)
        server_dim = server.copy()
        server_dim.thumbnail((10_000, SERVER_MAX_H_DIM), Image.LANCZOS)
        # counter_dim's own width cap (COUNTER_MAX_W_DIM) is actually wider
        # than the full-size server, let alone the much-shorter server_dim --
        # so middle_frame's dimmed-mode reservation uses server_dim's own
        # width specifically (matching self._server_w's role below), not the
        # composite's, or a visual round would reserve MORE space than a
        # plain round despite showing the smaller backdrop.
        self._server_w_dim = server_dim.width

        # Stacking these as two separate Tk Labels (the previous approach)
        # doesn't work: Tkinter paints each Label's own opaque bg wherever
        # its image is transparent, so the counter's transparent pixels hid
        # the server underneath instead of showing it through. Merging them
        # into one PIL image first (real alpha compositing) is the same fix
        # already used for slice_ui.py's pizza pieces and plate.
        stage = self._composite_backdrop(
            server_full, counter_full,
            y_shift=round(server_full.height * COUNTER_Y_SHIFT_FRACTION))
        stage_dim = self._dim(self._composite_backdrop(
            server_dim, counter_dim,
            y_shift=round(server_dim.height * COUNTER_Y_SHIFT_FRACTION)))
        self._stage_img = ImageTk.PhotoImage(stage)
        self._stage_img_dim = ImageTk.PhotoImage(stage_dim)

    @staticmethod
    def _composite_backdrop(server_img, counter_img, y_shift=0):
        """Merge the counter onto the server -- centered over the server's
        own width (clamped so it never overhangs to the left of it), and
        dropped y_shift pixels below flush-bottom with it (so a bigger
        counter still reveals more of the server than a merely-bigger,
        flush one would) -- into one image."""
        server_w, server_h = server_img.size
        counter_w, counter_h = counter_img.size
        counter_left = max(0, (server_w - counter_w) // 2)
        canvas_w = max(server_w, counter_left + counter_w)
        canvas_h = max(server_h + y_shift, counter_h)
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        canvas.paste(server_img, (0, 0), server_img)
        canvas.paste(counter_img, (counter_left, canvas_h - counter_h), counter_img)
        return canvas

    @staticmethod
    def _dim(pil_img, alpha=DIM_ALPHA):
        r, g, b, a = pil_img.split()
        a = a.point(lambda v: v * alpha // 255)
        return Image.merge("RGBA", (r, g, b, a))

    # ------------------------------------------------------------- build
    def _build(self):
        self.bubble_frame = tk.Frame(self.root, bg=BUBBLE_BG,
                                     highlightbackground=BUBBLE_BORDER,
                                     highlightthickness=3)
        self.bubble_frame.pack(fill="x", padx=20, pady=(16, 8))

        self.bubble_text = tk.Label(self.bubble_frame, text="", bg=BUBBLE_BG, fg=TEXT,
                                    font=("Helvetica", 18, "bold"), wraplength=900,
                                    justify="left")
        self.bubble_text.pack(padx=16, pady=(12, 4), anchor="w")

        self.bubble_toppings = tk.Frame(self.bubble_frame, bg=BUBBLE_BG)
        self.bubble_toppings.pack(padx=16, pady=(0, 12), anchor="w")

        # server+counter, and the checklist/shopping-list/board area, all
        # share this one stage (place(), not separate packed sections), so
        # they read as one scene rather than visually distinct blocks --
        # server and counter are pre-merged into one image (see
        # _load_backdrop_images/_composite_backdrop -- stacking them as
        # separate Tk Labels doesn't blend their transparency correctly),
        # sitting at the bottom-left, and middle_frame starts just to the
        # right of the server and is free to grow down over the counter if
        # its content needs the room, since it's always lifted above both.
        self.stage_frame = tk.Frame(self.root, bg=BG)
        self.stage_frame.pack(fill="both", expand=True, padx=20, pady=8)
        self.stage_frame.pack_propagate(False)

        self.stage_backdrop_label = tk.Label(self.stage_frame, image=self._stage_img, bg=BG)
        self.stage_backdrop_label.place(relx=0, rely=1.0, anchor="sw")

        self.middle_frame = tk.Frame(self.stage_frame, bg=BG)
        self.middle_frame.place(x=self._server_w + 20, y=0)  # re-placed per
        # round in _fit_to_screen, which knows whether the dim backdrop is
        # showing; this initial value just matches the non-dimmed default.
        self.middle_frame.lift()

        self._middle_canvas = tk.Canvas(self.middle_frame, bg=BG, highlightthickness=0)
        self._middle_scrollbar = tk.Scrollbar(self.middle_frame, orient="vertical",
                                              command=self._middle_canvas.yview)
        self._middle_canvas.configure(yscrollcommand=self._middle_scrollbar.set)
        self._middle_scrollbar.pack(side="right", fill="y")
        self._middle_canvas.pack(side="left", fill="both", expand=True)

        self._middle_inner = tk.Frame(self._middle_canvas, bg=BG)
        middle_window = self._middle_canvas.create_window(0, 0, window=self._middle_inner, anchor="nw")

        def _reposition_inner(_=None):
            # The canvas is sized to middle_inner's own natural content
            # (see _fit_to_screen), so they normally match exactly; this
            # only does something when content is too big to fit at all
            # (many kids' worth of pizza bases) and the canvas gets capped
            # smaller -- then clamp to the top-left and let scrolling
            # (scrollregion, below) reach the rest instead of centering.
            self._middle_canvas.configure(scrollregion=self._middle_canvas.bbox("all"))
            cw, ch = self._middle_canvas.winfo_width(), self._middle_canvas.winfo_height()
            iw, ih = self._middle_inner.winfo_reqwidth(), self._middle_inner.winfo_reqheight()
            x, y = max(0, (cw - iw) // 2), max(0, (ch - ih) // 2)
            self._middle_canvas.coords(middle_window, x, y)

        self._middle_inner.bind("<Configure>", _reposition_inner)
        self._middle_canvas.bind("<Configure>", _reposition_inner)

        def _scroll(event):
            delta = -1 * (event.delta // 120) if event.delta else (1 if event.num == 5 else -1)
            self._middle_canvas.yview_scroll(delta, "units")

        def _bind_wheel(_):
            self._middle_canvas.bind_all("<MouseWheel>", _scroll)
            self._middle_canvas.bind_all("<Button-4>", _scroll)
            self._middle_canvas.bind_all("<Button-5>", _scroll)

        def _unbind_wheel(_):
            self._middle_canvas.unbind_all("<MouseWheel>")
            self._middle_canvas.unbind_all("<Button-4>")
            self._middle_canvas.unbind_all("<Button-5>")

        self._middle_canvas.bind("<Enter>", _bind_wheel)
        self._middle_canvas.bind("<Leave>", _unbind_wheel)

        self.plain_panel = tk.Frame(self._middle_inner, bg=BG)

        self.visual_frame = tk.Frame(self._middle_inner, bg=BG)
        inventory_box, self.top_inventory_frame = self._build_titled_box(
            self.visual_frame, "Inventory")
        inventory_box.pack(pady=(0, 12))
        row = tk.Frame(self.visual_frame, bg=BG)
        row.pack(fill="both", expand=True)
        self.left_panel_frame = tk.Frame(row, bg=BG)
        self.left_panel_frame.pack(side="left", fill="y", padx=(0, 16))
        self.center_board_frame = tk.Frame(row, bg=BG)
        self.center_board_frame.pack(side="left", fill="both", expand=True)
        self.right_panel_frame = tk.Frame(row, bg=BG)
        self.right_panel_frame.pack(side="left", fill="y", padx=(16, 0))

    def _set_backdrop_dim(self, dimmed):
        self._dimmed = dimmed
        self.stage_backdrop_label.configure(
            image=self._stage_img_dim if dimmed else self._stage_img)
        # Re-assert stacking order every time this is called (every screen
        # transition): the checklist/shopping-list/board area stays above
        # the backdrop.
        self.middle_frame.lift()

    def _make_button(self, parent, text, command):
        lbl = tk.Label(parent, text=text, bg=BTN_BG, fg=TEXT,
                       font=("Helvetica", 16, "bold"), padx=16, pady=6,
                       bd=4, relief="raised", cursor="hand2")
        lbl.bind("<Button-1>", lambda e: command())
        lbl.bind("<Enter>", lambda e: lbl.configure(bg=BTN_ACTIVE))
        lbl.bind("<Leave>", lambda e: lbl.configure(bg=BTN_BG))
        return lbl

    def _build_titled_box(self, parent, title, title_font_size=15):
        """An off-white bordered box with a bold title at top. Returns
        (box, content) -- pack `box` wherever it goes, and put children in
        `content`."""
        box = tk.Frame(parent, bg=BUBBLE_BG, highlightbackground=BUBBLE_BORDER,
                       highlightthickness=2)
        tk.Label(box, text=title, bg=BUBBLE_BG, fg=TEXT,
                font=("Helvetica", title_font_size, "bold")).pack(pady=(10, 6), padx=16)
        content = tk.Frame(box, bg=BUBBLE_BG)
        content.pack(padx=16, pady=(0, 14))
        return box, content

    # ------------------------------------------------------------- bubble
    def _topping_icon(self, name, size=TOPPING_ICON_PX):
        key = (name, size)
        if key not in self._topping_icons:
            pil_img = Image.open(os.path.join(self.toppings_dir, f"{name}.png")).convert("RGBA")
            pil_img.thumbnail((size, size), Image.LANCZOS)
            self._topping_icons[key] = ImageTk.PhotoImage(pil_img)
        return self._topping_icons[key]

    def _render_bubble(self, text, tpk, toppings):
        self.bubble_text.configure(text=text)
        for w in self.bubble_toppings.winfo_children():
            w.destroy()
        if tpk and toppings:
            for name, k in zip(toppings, tpk):
                row = tk.Frame(self.bubble_toppings, bg=BUBBLE_BG)
                row.pack(side="left", padx=(0, 14))
                tk.Label(row, image=self._topping_icon(name), bg=BUBBLE_BG).pack(side="left")
                tk.Label(row, text=f"x{k}", bg=BUBBLE_BG, fg=TEXT,
                        font=("Helvetica", 14, "bold")).pack(side="left", padx=(4, 0))
        self._show()

    def server(self, text, tpk, toppings):
        if self._closed:
            return
        self._render_bubble(text, tpk, toppings)

    def display(self, text, a, b):
        if self._closed:
            return
        self._render_bubble(text, None, None)

    # ----------------------------------------------------------- checklist
    def _build_checklist_row(self, parent, t_inv, mistakes, i, name, big=False):
        locked = mistakes[i] % 2 == 0 and mistakes[i] != -1
        base_bg = BUBBLE_BG if big else BG
        row_bg = base_bg
        icon_px = CHECKLIST_ICON_PX if big else TOPPING_ICON_PX
        font_size = 16 if big else 13
        row = tk.Frame(parent, bg=row_bg)

        tk.Label(row, image=self._topping_icon(name, icon_px), bg=row_bg).pack(
            side="left", padx=(0, 10 if big else 8))
        tk.Label(row, text=str(t_inv[i]), bg=row_bg,
                fg= TEXT,
                font=("Helvetica", font_size, "bold"), width=4).pack(side="left")

        var = tk.BooleanVar(value=bool(self._checklist_state.get(i, False)))
        cb = tk.Checkbutton(row, variable=var, bg=row_bg, activebackground=row_bg,
                            state= "normal")
        cb.pack(side="left", padx=8)
        return row, var

    def _render_checklist_panel(self, parent, t_inv, mistakes, toppings):
        for w in parent.winfo_children():
            w.destroy()
        check_vars = {}
        for i, name in enumerate(toppings):
            row, var = self._build_checklist_row(parent, t_inv, mistakes, i, name)
            row.pack(pady=4, anchor="w")
            check_vars[i] = var

        submit = self._make_button(parent, "Submit", lambda: self._done.set(1))
        submit.pack(pady=(12, 0))
        return check_vars

    def _render_checklist_grid(self, parent, t_inv, mistakes, toppings):
        for w in parent.winfo_children():
            w.destroy()
        box, content = self._build_titled_box(
            parent, f"This is our inventory. Check the ingredients we have enough of!", title_font_size=17)
        box.pack(expand=True)

        grid = tk.Frame(content, bg=BUBBLE_BG)
        grid.pack()
        check_vars = {}
        for i, name in enumerate(toppings):
            row, var = self._build_checklist_row(grid, t_inv, mistakes, i, name, big=True)
            r, c = divmod(i, CHECKLIST_GRID_COLS)
            row.grid(row=r, column=c, padx=16, pady=10, sticky="w")
            check_vars[i] = var

        submit = self._make_button(content, "Submit", lambda: self._done.set(1))
        submit.pack(pady=(14, 0))
        return check_vars

    def _collect_checklist(self, check_vars, mistakes, toppings):
        enough = []
        for i in range(len(toppings)):
            # Backend contract: 0 == player said "enough", 1 == player said
            # "not enough".  A checked box means the player said "enough".
            if mistakes[i] % 2 == 0 and mistakes[i] != -1:
                enough.append(0 if self._checklist_state.get(i, False) else 1)
            else:
                val = check_vars[i].get()
                self._checklist_state[i] = val
                enough.append(0 if val else 1)
        return enough

    def askEnough(self, num_kids, tpk, t_inv, mistakes, toppings, allow_pizza_visual):
        if self._closed:
            return [0] * len(toppings)
        self._num_kids = num_kids
        if allow_pizza_visual:
            return self._ask_enough_visual(t_inv, mistakes, toppings)
        return self._ask_enough_plain(t_inv, mistakes, toppings)

    def _ask_enough_plain(self, t_inv, mistakes, toppings):
        if self._closed:
            return [0] * len(toppings)
        self._set_backdrop_dim(False)
        self.visual_frame.pack_forget()
        self.plain_panel.pack(fill="both", expand=True)

        check_vars = self._render_checklist_grid(self.plain_panel, t_inv, mistakes, toppings)

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)
        if self._closed:
            return [0] * len(toppings)
        return self._collect_checklist(check_vars, mistakes, toppings)

    # -------------------------------------------------------- pizza visual
    def _get_pizza_board(self, t_inv, toppings):
        if self._pizza_board is None:
            items = [(name, os.path.join(self.toppings_dir, f"{name}.png")) for name in toppings]
            initial_inventory = {name: t_inv[i] for i, name in enumerate(toppings)}
            self._pizza_board = PlacementBoard(
                base_image_path=os.path.join(self.image_dir, "pizza.png"),
                items=items, base_count=self._num_kids,
                initial_inventory=initial_inventory, show_item_switcher=True,
                base_px=PIZZA_BASE_PX, placement_circle_fraction=PIZZA_CIRCLE_FRACTION,
                max_board_width=BOARD_MAX_WIDTH_SHARED)
        return self._pizza_board

    def _reset_pizza_board(self, board):
        board.reset()
        board.render(self.top_inventory_frame, self.center_board_frame)

    def _render_pizza_reset(self, board):
        for w in self.left_panel_frame.winfo_children():
            w.destroy()
        reset_btn = self._make_button(
            self.left_panel_frame, "Reset", lambda: self._reset_pizza_board(board))
        reset_btn.pack(pady=(0, 8))

    def _ask_enough_visual(self, t_inv, mistakes, toppings):
        if self._closed:
            return [0] * len(toppings)
        self._set_backdrop_dim(True)
        self.plain_panel.pack_forget()
        self.visual_frame.pack(fill="both", expand=True)

        board = self._get_pizza_board(t_inv, toppings)
        board.render(self.top_inventory_frame, self.center_board_frame)
        self._render_pizza_reset(board)

        check_vars = self._render_checklist_panel(self.right_panel_frame, t_inv, mistakes, toppings)

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)
        if self._closed:
            return [0] * len(toppings)
        return self._collect_checklist(check_vars, mistakes, toppings)

    # ----------------------------------------------------------- shoplist
    def _render_static_inventory(self, parent, t_inv, toppings):
        for w in parent.winfo_children():
            w.destroy()
        box, content = self._build_titled_box(parent, "Inventory")
        box.pack()

        for i, name in enumerate(toppings):
            row = tk.Frame(content, bg=BUBBLE_BG)
            row.pack(pady=4, anchor="w")
            tk.Label(row, image=self._topping_icon(name), bg=BUBBLE_BG).pack(side="left", padx=(0, 8))
            tk.Label(row, text=str(t_inv[i]), bg=BUBBLE_BG, fg=TEXT,
                    font=("Helvetica", 13, "bold"), width=4).pack(side="left")
        return box

    def _render_shoplist_panel(self, parent, mistakes, warnings, toppings):
        for w in parent.winfo_children():
            w.destroy()
        box, content = self._build_titled_box(parent, "Shopping List")
        box.pack()

        entries = {}
        for i, name in enumerate(toppings):
            if mistakes[i] not in (2, 3):
                continue
            locked = warnings[i] == 0
            row_bg = LOCKED_BG if locked else BUBBLE_BG
            row = tk.Frame(content, bg=row_bg)
            row.pack(pady=4, anchor="w")

            tk.Label(row, image=self._topping_icon(name), bg=row_bg).pack(side="left", padx=(0, 8))

            if locked:
                tk.Label(row, text=str(self._shoplist_state.get(i, 0)), bg=row_bg,
                        fg=LOCKED_FG, font=("Helvetica", 13, "bold"), width=6).pack(side="left")
            else:
                entry = tk.Entry(row, width=6, font=("Helvetica", 13))
                entry.insert(0, str(self._shoplist_state.get(i, 0)))
                entry.pack(side="left")
                entries[i] = entry

        submit = self._make_button(content, "Submit", lambda: self._done.set(1))
        submit.pack(pady=(12, 0))
        return entries

    def _collect_shoplist(self, entries, mistakes, warnings, toppings):
        added = [0] * len(toppings)
        for i in range(len(toppings)):
            if mistakes[i] not in (2, 3):
                continue
            if warnings[i] == 0:
                added[i] = self._shoplist_state.get(i, 0)
            else:
                raw = entries[i].get().strip()
                val = int(raw) if raw.isdigit() else 0
                self._shoplist_state[i] = val
                added[i] = val
        return added

    def prompt(self, kids, tpk, t_inv, mistakes, warnings, toppings, allow_pizza_visual):
        if self._closed:
            return [0] * len(toppings)
        self._num_kids = kids
        if allow_pizza_visual:
            return self._prompt_visual(t_inv, mistakes, warnings, toppings)
        return self._prompt_plain(t_inv, mistakes, warnings, toppings)

    def _prompt_plain(self, t_inv, mistakes, warnings, toppings):
        if self._closed:
            return [0] * len(toppings)
        self._set_backdrop_dim(False)
        self.visual_frame.pack_forget()
        self.plain_panel.pack(fill="both", expand=True)

        for w in self.plain_panel.winfo_children():
            w.destroy()
        row = tk.Frame(self.plain_panel, bg=BG)
        row.pack(expand=True)

        inv_container = tk.Frame(row, bg=BG)
        inv_container.pack(side="left", padx=(0, 20))
        self._render_static_inventory(inv_container, t_inv, toppings)

        shop_container = tk.Frame(row, bg=BG)
        shop_container.pack(side="left")
        entries = self._render_shoplist_panel(shop_container, mistakes, warnings, toppings)

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)
        if self._closed:
            return [0] * len(toppings)
        return self._collect_shoplist(entries, mistakes, warnings, toppings)

    def _prompt_visual(self, t_inv, mistakes, warnings, toppings):
        if self._closed:
            return [0] * len(toppings)
        self._set_backdrop_dim(True)
        self.plain_panel.pack_forget()
        self.visual_frame.pack(fill="both", expand=True)

        board = self._get_pizza_board(t_inv, toppings)
        board.render(self.top_inventory_frame, self.center_board_frame)
        self._render_pizza_reset(board)

        entries = self._render_shoplist_panel(self.right_panel_frame, mistakes, warnings, toppings)

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)
        if self._closed:
            return [0] * len(toppings)
        return self._collect_shoplist(entries, mistakes, warnings, toppings)

    # ------------------------------------------------------------- cupcakes
    def _get_cupcake_board(self, num_kids, num_cakes):
        if self._cupcake_board is None:
            items = [("cupcake", os.path.join(self.image_dir, "cupcake.png"))]
            self._cupcake_board = PlacementBoard(
                base_image_path=os.path.join(self.image_dir, "plate.png.webp"),
                items=items, base_count=num_kids,
                initial_inventory={"cupcake": num_cakes}, show_item_switcher=True,
                placement_circle_fraction=CUPCAKE_CIRCLE_FRACTION,
                max_board_width=BOARD_MAX_WIDTH_SHARED)
        return self._cupcake_board

    def _render_number_answer(self, parent):
        for w in parent.winfo_children():
            w.destroy()
        answer_var = tk.StringVar(value="")
        entry = tk.Entry(parent, textvariable=answer_var, width=6, font=("Helvetica", 20))
        entry.pack(pady=(20, 10))
        entry.bind("<Return>", lambda e: self._done.set(1))
        submit = self._make_button(parent, "Submit", lambda: self._done.set(1))
        submit.pack()
        entry.focus_set()
        return answer_var

    @staticmethod
    def _collect_number_answer(answer_var):
        raw = answer_var.get().strip()
        return int(raw) if raw.lstrip("-").isdigit() else 0

    def quest(self, allow_cupcake_visual, num_kids, num_cakes):
        if self._closed:
            return 0
        if allow_cupcake_visual:
            return self._quest_visual(num_kids, num_cakes)
        return self._quest_plain(num_kids, num_cakes)

    def _quest_plain(self, num_kids, num_cakes):
        if self._closed:
            return 0
        self._set_backdrop_dim(False)
        self.visual_frame.pack_forget()
        self.plain_panel.pack(fill="both", expand=True)

        answer_var = self._render_number_answer(self.plain_panel)

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)
        if self._closed:
            return 0
        return self._collect_number_answer(answer_var)

    def _quest_visual(self, num_kids, num_cakes):
        if self._closed:
            return 0
        self._set_backdrop_dim(True)
        self.plain_panel.pack_forget()
        self.visual_frame.pack(fill="both", expand=True)

        for w in self.right_panel_frame.winfo_children():
            w.destroy()

        board = self._get_cupcake_board(num_kids, num_cakes)
        board.render(self.top_inventory_frame, self.center_board_frame)

        answer_var = self._render_number_answer(self.left_panel_frame)

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)
        if self._closed:
            return 0
        return self._collect_number_answer(answer_var)

    # ------------------------------------------------------------ window
    def _show(self):
        if not self._shown:
            self.root.deiconify()
            self._shown = True
        self.root.update_idletasks()
        self._fit_to_screen()

    def _fit_to_screen(self):
        # Cap the window to the screen so it can never grow taller/wider
        # than the display. middle_frame, server, and counter all share
        # stage_frame via place() (see _build), so none of them propagate
        # a natural size to it the way pack()/grid() children would --
        # stage_frame's (and therefore the window's) size has to be
        # computed and set explicitly here. Re-applied on every screen
        # transition since required content size changes each round.
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        # winfo_screenheight() is the full physical display height, not the
        # usable work area -- it doesn't exclude the menu bar/title bar, so
        # leave a fixed margin in addition to the percentage, or a window
        # sized to "90% of screen" can still be taller than what's actually
        # available to place it in.
        max_w, max_h = int(sw * 0.95), int(sh * 0.85) - 40

        bubble_h = self.bubble_frame.winfo_reqheight()
        # Reserve space for whichever backdrop image is actually showing
        # right now, not always the full-size one -- during a pizza/cupcake
        # visual (self._dimmed) the backdrop shrinks to the small dim
        # version, and reserving room for the big one anyway (its previous
        # behavior) wasted most of the window on empty space, squeezing the
        # visual into whatever was left. backdrop_w/h are the merged
        # server+counter image's own footprint (see _composite_backdrop --
        # it can be wider than the server alone if the counter overhangs);
        # middle_frame's own x-offset uses just the SERVER's own width
        # (self._server_w / self._server_w_dim), not the composite's, so it
        # starts just past the server and is free to overlap any counter
        # overhang -- the dim counter's own width cap happens to be even
        # wider than the full-size server, so this distinction matters more
        # in dim mode, not less.
        if self._dimmed:
            backdrop_img = self._stage_img_dim
            reserve_w = self._server_w_dim
        else:
            backdrop_img = self._stage_img
            reserve_w = self._server_w
        backdrop_w = backdrop_img.width()
        backdrop_h = backdrop_img.height()
        self.middle_frame.place(x=reserve_w + 20, y=0)

        # Size the canvas to middle_inner's own natural content first (not
        # forced to fill all available space) -- small content (e.g. a
        # short checklist) should stay its natural size, sitting above the
        # counter rather than stretching down to cover it; only content
        # too big to fit at all should be capped and scroll. Based on
        # reserve_w (where middle_frame actually starts), not backdrop_w --
        # middle_frame is free to overlap the rest of the backdrop's own
        # width (the counter), so that space isn't unavailable to it.
        available_w = max(200, max_w - reserve_w - 20)
        available_h = max(150, max_h - bubble_h - 40)
        inner_w = self._middle_inner.winfo_reqwidth()
        inner_h = self._middle_inner.winfo_reqheight()
        self._middle_canvas.configure(width=min(inner_w, available_w),
                                      height=min(inner_h, available_h))
        self.root.update_idletasks()

        middle_w = self.middle_frame.winfo_reqwidth()
        middle_h = self.middle_frame.winfo_reqheight()
        stage_w = min(max_w, backdrop_w + 20 + middle_w)
        stage_h = min(max_h - bubble_h - 20, max(backdrop_h, middle_h))
        self.stage_frame.configure(width=stage_w, height=stage_h)
        self.root.update_idletasks()

        w = min(self.root.winfo_reqwidth(), max_w)
        h = min(self.root.winfo_reqheight(), max_h)
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 8)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        # resizable(False, False) alone isn't reliable here -- on macOS it
        # sets its own maxsize tied to the screen's usable work area (minus
        # window-manager chrome), not to the geometry just requested, which
        # silently caps a tall request below what geometry() alone would
        # give. Pin minsize/maxsize explicitly to this exact size so there
        # is no ambiguity about what's actually allowed.
        self.root.resizable(False, False)
        self.root.minsize(w, h)
        self.root.maxsize(w, h)

    def close(self):
        if not self._closed:
            self._closed = True
            try:
                self.root.destroy()
            except tk.TclError:
                pass

    def _on_close(self):
        self._closed = True
        self._done.set(1)
        try:
            self.root.destroy()
        except tk.TclError:
            pass
