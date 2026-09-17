"""Front end for the bySlice.py pizza-fraction game.

A single Tkinter window (reused across rounds, matching coin_ui.py,
grocery_ui.py, and party_ui.py) with two symmetric customer columns --
left (customer1, the plain-named speak/makeCuts.../onPlate... slot) and
right (customer2, the "2"-suffixed slot) -- sharing one counter along the
bottom.

Each pizza is rendered as a stack of same-size, same-position Labels (one
per slice-image piece for the current slice count), so the pieces visually
combine into a whole pizza via their transparent backgrounds. During
handover, a click's target piece is found by testing each piece's real
pixel alpha at the click point (checking the topmost piece first), not by
widget bounding boxes -- every piece's Label covers the whole pizza, so
bounding-box hit testing alone could never reach anything but the
topmost piece.

Usage from bySlice.py:

    from slice_ui import SliceUI
    ui = SliceUI(image_dir="sliceimages")
    ui.speak("I'd like 3/4 pizza")
    slice1, slice2 = ui.makeCuts(denom2)
    slices1, slices2 = ui.onPlate(denom, denom2)
"""

import os
import tkinter as tk

from PIL import Image, ImageTk

PARTY_IMAGE_DIR = "partyimages"  # counter.png / plate.png.webp are reused from the party game

BG = "#fdf6e3"
TEXT = "#3b2f1e"
BUBBLE_BG = "#ffffff"
BUBBLE_BORDER = "#3b2f1e"
BTN_BG = "#ffd27f"
BTN_ACTIVE = "#ffbe4d"
PLATE_BG = "#f6ead1"

CUSTOMER_PX = 160
PIZZA_PX = 260
COUNTER_MAX_W = 900
PLATE_PX = 220
PLATE_PIECE_PX = 50
PLATE_PIECE_COLS = 4


class SliceUI:
    def __init__(self, image_dir="sliceimages"):
        self.image_dir = image_dir

        self.root = tk.Tk()
        self.root.title("Pizza Slices")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._closed = False
        self._shown = False
        self._done = tk.IntVar(value=0)

        self._load_static_images()
        self._load_slice_images()
        self._build()
        self.root.withdraw()

    # ------------------------------------------------------------- images
    def _load_static_images(self):
        customer1 = Image.open(os.path.join(self.image_dir, "customer1.png")).convert("RGBA")
        customer1.thumbnail((CUSTOMER_PX, CUSTOMER_PX), Image.LANCZOS)
        self._customer1_img = ImageTk.PhotoImage(customer1)

        customer2 = Image.open(os.path.join(self.image_dir, "customer2.png")).convert("RGBA")
        customer2.thumbnail((CUSTOMER_PX, CUSTOMER_PX), Image.LANCZOS)
        self._customer2_img = ImageTk.PhotoImage(customer2)

        counter = Image.open(os.path.join(PARTY_IMAGE_DIR, "counter.png")).convert("RGBA")
        counter.thumbnail((COUNTER_MAX_W, 10_000), Image.LANCZOS)
        self._counter_img = ImageTk.PhotoImage(counter)

        plate = Image.open(os.path.join(PARTY_IMAGE_DIR, "plate.png.webp")).convert("RGBA")
        plate.thumbnail((PLATE_PX, PLATE_PX), Image.LANCZOS)
        self._plate_img = ImageTk.PhotoImage(plate)

    def _load_slice_images(self):
        # self._slice_pil keeps the resized PIL Image (with real alpha
        # data) for hit-testing; self._slice_photo/_photo_small are the Tk
        # PhotoImages actually drawn (full pizza size, and a smaller size
        # for once a piece is sitting on the plate).
        self._slice_pil = {}
        self._slice_photo = {}
        self._slice_photo_small = {}
        for n in range(1, 6):
            filenames = ["1slice.PNG"] if n == 1 else [f"{n}slice-{k}.PNG" for k in range(1, n + 1)]
            for k, fname in enumerate(filenames, start=1):
                pil_img = Image.open(os.path.join(self.image_dir, fname)).convert("RGBA")
                pil_full = pil_img.resize((PIZZA_PX, PIZZA_PX), Image.LANCZOS)
                self._slice_pil[(n, k)] = pil_full
                self._slice_photo[(n, k)] = ImageTk.PhotoImage(pil_full)
                pil_small = pil_img.resize((PLATE_PIECE_PX, PLATE_PIECE_PX), Image.LANCZOS)
                self._slice_photo_small[(n, k)] = ImageTk.PhotoImage(pil_small)

    # ------------------------------------------------------------- build
    def _build(self):
        row = tk.Frame(self.root, bg=BG)
        row.pack(fill="both", expand=True, padx=20, pady=20)

        self.left_zone = tk.Frame(row, bg=BG)
        self.left_zone.pack(side="left", fill="both", expand=True)
        self.right_zone = tk.Frame(row, bg=BG)
        self.right_zone.pack(side="left", fill="both", expand=True)

        self.bubble1, self._bubble1_text = self._build_bubble(self.left_zone)
        self.bubble1.pack(pady=(0, 10))
        left_row = tk.Frame(self.left_zone, bg=BG)
        left_row.pack()
        tk.Label(left_row, image=self._customer1_img, bg=BG).pack(side="left", padx=(0, 16))
        self.pizza_col1 = tk.Frame(left_row, bg=BG)
        self.pizza_col1.pack(side="left")

        self.bubble2, self._bubble2_text = self._build_bubble(self.right_zone)
        self.bubble2.pack(pady=(0, 10))
        right_row = tk.Frame(self.right_zone, bg=BG)
        right_row.pack()
        self.pizza_col2 = tk.Frame(right_row, bg=BG)
        self.pizza_col2.pack(side="left")
        tk.Label(right_row, image=self._customer2_img, bg=BG).pack(side="left", padx=(16, 0))

        self.counter_label = tk.Label(self.root, image=self._counter_img, bg=BG)
        self.counter_label.pack(side="bottom", pady=(10, 0))

    def _build_bubble(self, parent):
        box = tk.Frame(parent, bg=BUBBLE_BG, highlightbackground=BUBBLE_BORDER,
                       highlightthickness=3)
        lbl = tk.Label(box, text="", bg=BUBBLE_BG, fg=TEXT, font=("Helvetica", 14, "bold"),
                       wraplength=260, justify="left")
        lbl.pack(padx=14, pady=10)
        return box, lbl

    def _make_button(self, parent, text, command):
        lbl = tk.Label(parent, text=text, bg=BTN_BG, fg=TEXT, font=("Helvetica", 14, "bold"),
                       padx=14, pady=6, bd=4, relief="raised", cursor="hand2")
        lbl.bind("<Button-1>", lambda e: command())
        lbl.bind("<Enter>", lambda e: lbl.configure(bg=BTN_ACTIVE))
        lbl.bind("<Leave>", lambda e: lbl.configure(bg=BTN_BG))
        return lbl

    # ------------------------------------------------------------- bubble
    def speak(self, text):
        if self._closed:
            return
        self._bubble1_text.configure(text=text)
        self._show()

    def speak2(self, text):
        if self._closed:
            return
        self._bubble2_text.configure(text=text)
        self._show()

    # ------------------------------------------------------------- cutPizza
    def makeCuts(self, denom2):
        if self._closed:
            return (1, None if denom2 is None else 1)

        self._cut_state = {"left": 1, "right": 1}
        active = ["left"] + (["right"] if denom2 is not None else [])

        for key in active:
            self._render_cut_pizza(key)
        if denom2 is None:
            for w in self.pizza_col2.winfo_children():
                w.destroy()

        submit = self._make_button(self.root, "Cut", lambda: self._done.set(1))
        submit.pack(side="bottom", pady=(6, 0))

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)
        try:
            submit.destroy()
        except tk.TclError:
            pass

        if self._closed:
            return (1, None if denom2 is None else 1)
        slice1 = self._cut_state["left"]
        slice2 = self._cut_state["right"] if denom2 is not None else None
        return (slice1, slice2)

    def _render_cut_pizza(self, key):
        col = self.pizza_col1 if key == "left" else self.pizza_col2
        for w in col.winfo_children():
            w.destroy()

        stack = tk.Frame(col, bg=BG, width=PIZZA_PX, height=PIZZA_PX)
        stack.pack()
        stack.pack_propagate(False)

        n = self._cut_state[key]
        for k in range(1, n + 1):
            lbl = tk.Label(stack, image=self._slice_photo[(n, k)], bg=BG, bd=0,
                           highlightthickness=0, cursor="hand2")
            lbl.place(x=0, y=0)
            lbl.bind("<Button-1>", lambda e, kk=key: self._cycle_pizza(kk))

        reset_btn = self._make_button(col, "New Pizza", lambda: self._reset_pizza(key))
        reset_btn.pack(pady=(8, 0))

    def _cycle_pizza(self, key):
        self._cut_state[key] = (self._cut_state[key] % 5) + 1
        self._render_cut_pizza(key)

    def _reset_pizza(self, key):
        self._cut_state[key] = 1
        self._render_cut_pizza(key)

    # ------------------------------------------------------------- handOver
    def onPlate(self, denom, denom2):
        if self._closed:
            return (0, None if denom2 is None else 0)

        self._handover_denom = {"left": denom, "right": denom2}
        active = ["left"] + (["right"] if denom2 is not None else [])
        self._pizzas = {"left": [], "right": []}
        self._plate_count = {"left": 0, "right": 0}

        for key in active:
            self._new_pizza(key)
        if denom2 is None:
            for w in self.pizza_col2.winfo_children():
                w.destroy()

        submit = self._make_button(self.root, "Hand Over", lambda: self._done.set(1))
        submit.pack(side="bottom", pady=(6, 0))

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)
        try:
            submit.destroy()
        except tk.TclError:
            pass

        if self._closed:
            return (0, None if denom2 is None else 0)
        slices1 = self._plate_count["left"]
        slices2 = self._plate_count["right"] if denom2 is not None else None
        return (slices1, slices2)

    def _new_pizza(self, key):
        n = self._handover_denom[key]
        pieces = [{"k": k, "on_plate": False} for k in range(1, n + 1)]
        self._pizzas[key].append(pieces)
        self._render_handover(key)

    def _render_handover(self, key):
        col = self.pizza_col1 if key == "left" else self.pizza_col2
        for w in col.winfo_children():
            w.destroy()

        n = self._handover_denom[key]
        pizzas_row = tk.Frame(col, bg=BG)
        pizzas_row.pack()

        for pizza_idx, pieces in enumerate(self._pizzas[key]):
            stack = tk.Frame(pizzas_row, bg=BG, width=PIZZA_PX, height=PIZZA_PX)
            stack.pack(side="left", padx=6)
            stack.pack_propagate(False)
            for piece in pieces:
                if piece["on_plate"]:
                    continue
                lbl = tk.Label(stack, image=self._slice_photo[(n, piece["k"])], bg=BG, bd=0,
                               highlightthickness=0, cursor="hand2")
                lbl.place(x=0, y=0)
                lbl.bind("<Button-1>",
                        lambda e, kk=key, pi=pizza_idx: self._pizza_piece_click(kk, pi, e.x, e.y))

        add_btn = self._make_button(col, "Add Pizza", lambda: self._new_pizza(key))
        add_btn.pack(pady=(8, 0))

        plate_box = tk.Frame(col, bg=PLATE_BG, highlightbackground=BUBBLE_BORDER,
                             highlightthickness=2)
        plate_box.pack(pady=(10, 0))
        plate_bg_lbl = tk.Label(plate_box, image=self._plate_img, bg=PLATE_BG)
        plate_bg_lbl.place(x=0, y=0)
        plate_grid = tk.Frame(plate_box, bg=PLATE_BG, width=PLATE_PX, height=PLATE_PX)
        plate_grid.pack()
        plate_grid.pack_propagate(False)

        i = 0
        for pizza_idx, pieces in enumerate(self._pizzas[key]):
            for piece_idx, piece in enumerate(pieces):
                if not piece["on_plate"]:
                    continue
                r, c = divmod(i, PLATE_PIECE_COLS)
                lbl = tk.Label(plate_grid, image=self._slice_photo_small[(n, piece["k"])],
                               bg=PLATE_BG, bd=0, highlightthickness=0, cursor="hand2")
                lbl.place(x=4 + c * (PLATE_PIECE_PX + 4), y=4 + r * (PLATE_PIECE_PX + 4))
                lbl.bind("<Button-1>",
                        lambda e, kk=key, pi=pizza_idx, ppi=piece_idx: self._plate_piece_click(kk, pi, ppi))
                i += 1

    def _pizza_piece_click(self, key, pizza_idx, x, y):
        n = self._handover_denom[key]
        pieces = self._pizzas[key][pizza_idx]
        # Topmost piece first (highest k was drawn last -> on top), so a
        # click in an area where pieces overlap resolves to whichever one
        # is actually visible there.
        for piece in sorted((p for p in pieces if not p["on_plate"]),
                            key=lambda p: p["k"], reverse=True):
            pil_img = self._slice_pil[(n, piece["k"])]
            if 0 <= x < PIZZA_PX and 0 <= y < PIZZA_PX and pil_img.getpixel((x, y))[3] > 10:
                piece["on_plate"] = True
                self._plate_count[key] += 1
                self._render_handover(key)
                return

    def _plate_piece_click(self, key, pizza_idx, piece_idx):
        piece = self._pizzas[key][pizza_idx][piece_idx]
        piece["on_plate"] = False
        self._plate_count[key] -= 1
        self._render_handover(key)

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
