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

BG = "#fdf6e3"
TEXT = "#3b2f1e"
BUBBLE_BG = "#ffffff"
BUBBLE_BORDER = "#3b2f1e"
LOCKED_BG = "#e8e2cf"
LOCKED_FG = "#9c8f6e"
BTN_BG = "#ffd27f"
BTN_ACTIVE = "#ffbe4d"

TOPPING_ICON_PX = 36
COUNTER_MAX_W = 1000
SERVER_MAX_H = 260
COUNTER_MAX_W_DIM = 500
SERVER_MAX_H_DIM = 130
DIM_ALPHA = 90  # out of 255


class PartyUI:
    def __init__(self, image_dir="partyimages", toppings_dir="shopimages"):
        self.image_dir = image_dir
        self.toppings_dir = toppings_dir

        self.root = tk.Tk()
        self.root.title("Birthday Party")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._closed = False
        self._shown = False
        self._done = tk.IntVar(value=0)

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

        counter_full = counter.copy()
        counter_full.thumbnail((COUNTER_MAX_W, 10_000), Image.LANCZOS)
        server_full = server.copy()
        server_full.thumbnail((10_000, SERVER_MAX_H), Image.LANCZOS)

        counter_dim = counter.copy()
        counter_dim.thumbnail((COUNTER_MAX_W_DIM, 10_000), Image.LANCZOS)
        server_dim = server.copy()
        server_dim.thumbnail((10_000, SERVER_MAX_H_DIM), Image.LANCZOS)

        self._counter_img = ImageTk.PhotoImage(counter_full)
        self._server_img = ImageTk.PhotoImage(server_full)
        self._counter_img_dim = ImageTk.PhotoImage(self._dim(counter_dim))
        self._server_img_dim = ImageTk.PhotoImage(self._dim(server_dim))

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

        self.middle_frame = tk.Frame(self.root, bg=BG)
        self.middle_frame.pack(fill="both", expand=True, padx=20, pady=8)

        self.plain_panel = tk.Frame(self.middle_frame, bg=BG)

        self.visual_frame = tk.Frame(self.middle_frame, bg=BG)
        self.top_inventory_frame = tk.Frame(self.visual_frame, bg=BG)
        self.top_inventory_frame.pack(fill="x", pady=(0, 12))
        row = tk.Frame(self.visual_frame, bg=BG)
        row.pack(fill="both", expand=True)
        self.left_panel_frame = tk.Frame(row, bg=BG)
        self.left_panel_frame.pack(side="left", fill="y", padx=(0, 16))
        self.center_board_frame = tk.Frame(row, bg=BG)
        self.center_board_frame.pack(side="left", fill="both", expand=True)
        self.right_panel_frame = tk.Frame(row, bg=BG)
        self.right_panel_frame.pack(side="left", fill="y", padx=(16, 0))

        self.backdrop_frame = tk.Frame(self.root, bg=BG)
        self.backdrop_frame.pack(fill="x", side="bottom", pady=(8, 0))

        self.server_label = tk.Label(self.backdrop_frame, image=self._server_img, bg=BG)
        self.server_label.pack(side="left", anchor="s", padx=(20, 0))

        self.counter_label = tk.Label(self.backdrop_frame, image=self._counter_img, bg=BG)
        self.counter_label.pack(side="left", anchor="s")

    def _set_backdrop_dim(self, dimmed):
        self.server_label.configure(image=self._server_img_dim if dimmed else self._server_img)
        self.counter_label.configure(image=self._counter_img_dim if dimmed else self._counter_img)

    def _make_button(self, parent, text, command):
        lbl = tk.Label(parent, text=text, bg=BTN_BG, fg=TEXT,
                       font=("Helvetica", 16, "bold"), padx=16, pady=6,
                       bd=4, relief="raised", cursor="hand2")
        lbl.bind("<Button-1>", lambda e: command())
        lbl.bind("<Enter>", lambda e: lbl.configure(bg=BTN_ACTIVE))
        lbl.bind("<Leave>", lambda e: lbl.configure(bg=BTN_BG))
        return lbl

    # ------------------------------------------------------------- bubble
    def _topping_icon(self, name):
        if name not in self._topping_icons:
            pil_img = Image.open(os.path.join(self.toppings_dir, f"{name}.png")).convert("RGBA")
            pil_img.thumbnail((TOPPING_ICON_PX, TOPPING_ICON_PX), Image.LANCZOS)
            self._topping_icons[name] = ImageTk.PhotoImage(pil_img)
        return self._topping_icons[name]

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
    def _render_checklist_panel(self, parent, t_inv, mistakes, toppings):
        for w in parent.winfo_children():
            w.destroy()
        check_vars = {}
        for i, name in enumerate(toppings):
            locked = mistakes[i] % 2 == 0 and mistakes[i] != -1
            row_bg = LOCKED_BG if locked else BG
            row = tk.Frame(parent, bg=row_bg)
            row.pack(pady=4, anchor="w")

            tk.Label(row, image=self._topping_icon(name), bg=row_bg).pack(side="left", padx=(0, 8))
            tk.Label(row, text=str(t_inv[i]), bg=row_bg,
                    fg=LOCKED_FG if locked else TEXT,
                    font=("Helvetica", 13, "bold"), width=4).pack(side="left")

            var = tk.BooleanVar(value=bool(self._checklist_state.get(i, False)))
            cb = tk.Checkbutton(row, variable=var, bg=row_bg, activebackground=row_bg,
                                state="disabled" if locked else "normal")
            cb.pack(side="left", padx=8)
            check_vars[i] = var

        submit = self._make_button(parent, "Submit", lambda: self._done.set(1))
        submit.pack(pady=(12, 0))
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
            return self._ask_enough_visual(t_inv, mistakes, toppings, tpk)
        return self._ask_enough_plain(t_inv, mistakes, toppings)

    def _ask_enough_plain(self, t_inv, mistakes, toppings):
        if self._closed:
            return [0] * len(toppings)
        self._set_backdrop_dim(False)
        self.visual_frame.pack_forget()
        self.plain_panel.pack(fill="both", expand=True)

        check_vars = self._render_checklist_panel(self.plain_panel, t_inv, mistakes, toppings)

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
                initial_inventory=initial_inventory, show_item_switcher=True)
        return self._pizza_board

    def _render_order_list(self, tpk, toppings):
        for w in self.left_panel_frame.winfo_children():
            w.destroy()
        for name, k in zip(toppings, tpk):
            row = tk.Frame(self.left_panel_frame, bg=BG)
            row.pack(pady=4, anchor="w")
            tk.Label(row, image=self._topping_icon(name), bg=BG).pack(side="left")
            tk.Label(row, text=f"x{k}", bg=BG, fg=TEXT,
                    font=("Helvetica", 13, "bold")).pack(side="left", padx=(6, 0))

    def _ask_enough_visual(self, t_inv, mistakes, toppings, tpk):
        if self._closed:
            return [0] * len(toppings)
        self._set_backdrop_dim(True)
        self.plain_panel.pack_forget()
        self.visual_frame.pack(fill="both", expand=True)

        board = self._get_pizza_board(t_inv, toppings)
        board.render(self.top_inventory_frame, self.center_board_frame)

        self._render_order_list(tpk, toppings)
        check_vars = self._render_checklist_panel(self.right_panel_frame, t_inv, mistakes, toppings)

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)
        if self._closed:
            return [0] * len(toppings)
        return self._collect_checklist(check_vars, mistakes, toppings)

    # ----------------------------------------------------------- shoplist
    def _render_shoplist_panel(self, parent, mistakes, warnings, toppings):
        for w in parent.winfo_children():
            w.destroy()
        entries = {}
        for i, name in enumerate(toppings):
            if mistakes[i] not in (2, 3):
                continue
            locked = warnings[i] == 0
            row_bg = LOCKED_BG if locked else BG
            row = tk.Frame(parent, bg=row_bg)
            row.pack(pady=4, anchor="w")

            tk.Label(row, image=self._topping_icon(name), bg=row_bg).pack(side="left", padx=(0, 8))

            if locked:
                tk.Label(row, text=str(self._shoplist_state.get(i, 0)), bg=row_bg,
                        fg=LOCKED_FG, font=("Helvetica", 13, "bold"), width=6).pack(side="left")
            else:
                entry = tk.Entry(row, width=6, font=("Helvetica", 13))
                entry.insert(0, "0")
                entry.pack(side="left")
                entries[i] = entry

        submit = self._make_button(parent, "Submit", lambda: self._done.set(1))
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
            return self._prompt_visual(t_inv, mistakes, warnings, toppings, tpk)
        return self._prompt_plain(mistakes, warnings, toppings)

    def _prompt_plain(self, mistakes, warnings, toppings):
        if self._closed:
            return [0] * len(toppings)
        self._set_backdrop_dim(False)
        self.visual_frame.pack_forget()
        self.plain_panel.pack(fill="both", expand=True)

        entries = self._render_shoplist_panel(self.plain_panel, mistakes, warnings, toppings)

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)
        if self._closed:
            return [0] * len(toppings)
        return self._collect_shoplist(entries, mistakes, warnings, toppings)

    def _prompt_visual(self, t_inv, mistakes, warnings, toppings, tpk):
        if self._closed:
            return [0] * len(toppings)
        self._set_backdrop_dim(True)
        self.plain_panel.pack_forget()
        self.visual_frame.pack(fill="both", expand=True)

        board = self._get_pizza_board(t_inv, toppings)
        board.render(self.top_inventory_frame, self.center_board_frame)

        self._render_order_list(tpk, toppings)
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
                initial_inventory={"cupcake": num_cakes}, show_item_switcher=True)
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
            self.root.update_idletasks()
            self._center_window()
            self._shown = True
        else:
            self.root.update_idletasks()

    def _center_window(self):
        w, h = self.root.winfo_width(), self.root.winfo_height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 4)}")

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
