"""Front end for the bySlice.py pizza-fraction game.

A single Tkinter window (reused across rounds, matching coin_ui.py,
grocery_ui.py, and party_ui.py) with two symmetric customers, side by
side -- customer1 (the plain-named speak/makeCuts.../onPlate... slot) on
the left, customer2 (the "2"-suffixed slot) on the right, each next to
their own pizza.

Each pizza is rendered as one image: the current slice count's pieces are
alpha-composited together with PIL into a single merged picture before
being shown (Tk doesn't composite separate same-position Labels' alpha
channels against each other -- each Label's own "transparent" pixels just
paint its own opaque background color over whatever's beneath it, so
naively stacking per-piece Labels hides everything but the topmost one).
During handover, a click's target piece is still found by testing each
underlying piece's real pixel alpha at the click point against the
one-per-piece PIL data kept for hit-testing (checking the topmost piece
first) -- the composited image is only for display; hit-testing never
relies on separate widgets per piece.

The right-hand customer column (customer2, speech bubble, its pizza) is
only shown while there's a second customer -- hidden via pack/pack_forget
whenever denom2 is None.

Usage from bySlice.py:

    from slice_ui import SliceUI
    ui = SliceUI(image_dir="sliceimages")
    ui.instruct("Cut the pizza to the right size!")
    ui.speak("I'd like 3/4 pizza")
    slice1, slice2 = ui.makeCuts(denom2)
    slices1, slices2 = ui.onPlate(denom, denom2)
    ui.customerServed()
"""

import os
import random
import tkinter as tk

from PIL import Image, ImageTk

from shared_root import get_shared_root

PARTY_IMAGE_DIR = "partyimages"  # plate.png.webp is reused from the party game

# bySlice.py wraps a hint-level-2+ target value in this exact escape
# sequence (a terminal underline code -- meaningless to Tkinter, so it's
# used here purely as a marker to detect and re-render as real emphasis).
UNDERLINE = "\033[4m"

BG = "#fdf6e3"
TEXT = "#3b2f1e"
BUBBLE_BG = "#ffffff"
BUBBLE_BORDER = "#3b2f1e"
BTN_BG = "#ffd27f"
BTN_ACTIVE = "#ffbe4d"
PLATE_BG = "#f6ead1"
EMPHASIS_COLOR = "#c0392b"  # matches coin_ui.py's WARN_FG, for consistency

CUSTOMER_PX = 450  # matches SERVER_MAX_H, party_ui.py's server png size
PIZZA_PX = 200
PIZZAS_PER_ROW = 2  # extra pizzas (Add Pizza) wrap to a new row instead of
                     # growing sideways, so the window's width never
                     # changes as more are added
PLATE_PX = 200
PLATE_PIECE_PX = 55
# The plate art is a circle that nearly fills its canvas edge-to-edge
# (~97% diameter, same asset reused from the party game's cupcake board,
# where this was measured directly against the source pixels). Plated
# pieces are scattered at random within a slightly smaller circle (leaving
# margin for each piece's own footprint) so they land visibly on the
# plate and can overlap naturally, like real slices piled up.
PLATE_CIRCLE_FRACTION = 0.85


class SliceUI:
    def __init__(self, image_dir="sliceimages"):
        self.image_dir = image_dir

        self.root = tk.Toplevel(get_shared_root())
        self.root.title("Pizza Slices")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._closed = False
        self._shown = False
        self._done = tk.IntVar(value=0)
        # Per-customer, one-time-ever-per-round "Add Pizza" allowance --
        # set (and reset fresh for the round) in makeCuts, then read by
        # BOTH makeCuts and onPlate, since a customer only ever gets one
        # extra pizza total, whichever phase they use it in.
        self._pizza_added = {"left": False, "right": False}
        # How many pizzas each customer ended the cut phase with -- reset
        # fresh in makeCuts, then read by onPlate so the handover phase
        # starts with exactly that many pizzas already carried over,
        # instead of resetting back down to one.
        self._cut_pizza_count = {"left": 1, "right": 1}
        self._cut_state = {"left": 1, "right": 1}
        # True only at the start of a brand new round -- makeCuts() resets
        # the cut state/pizza count/Add Pizza allowance when this is True
        # (and clears it), so a wrong guess (which makes bySlice.py call
        # makeCuts() again within the SAME round) doesn't wipe them out.
        # onPlate() sets this back to True once the round's handover phase
        # begins, so the next round's first makeCuts() call resets fresh.
        self._pending_new_round = True
        # Mirrors _pending_new_round for the handover phase: True only at
        # the start of a brand new round's handover, so onPlate() creates
        # the carried-over pizzas and clears the plate just once per round
        # -- a wrong guess (bySlice.py calling onPlate() again within the
        # SAME round) leaves the plate and pizzas exactly as the player
        # left them instead of wiping the plate back to empty. makeCuts()
        # sets this back to True once a new round's cut phase begins.
        self._pending_new_handover = True
        # Cumulative count of customers served this session (one SliceUI
        # instance lives for one serveCustomers() call) -- bySlice.py calls
        # customerServed() once per customer whose order comes back correct.
        self.customers_served = 0

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

        plate = Image.open(os.path.join(PARTY_IMAGE_DIR, "plate.png.webp")).convert("RGBA")
        plate.thumbnail((PLATE_PX, PLATE_PX), Image.LANCZOS)
        # Resize to an exact square (thumbnail only caps, doesn't pad) so
        # the plate's own center/radius math in _random_plate_position is
        # exact, not approximate.
        self._plate_pil = plate.resize((PLATE_PX, PLATE_PX), Image.LANCZOS)

    def _load_slice_images(self):
        # self._slice_pil keeps the resized PIL Image (with real alpha
        # data) for hit-testing and for compositing onto the pizza/plate;
        # self._slice_photo is the full-pizza-size Tk PhotoImage actually
        # drawn. self._slice_pil_plate is a separate, plate-scale PIL
        # resize used only once a piece is sitting on the plate.
        self._slice_pil = {}
        self._slice_photo = {}
        self._slice_pil_plate = {}
        for n in range(1, 6):
            filenames = ["1slice.PNG"] if n == 1 else [f"{n}slice-{k}.PNG" for k in range(1, n + 1)]
            for k, fname in enumerate(filenames, start=1):
                pil_img = Image.open(os.path.join(self.image_dir, fname)).convert("RGBA")
                pil_full = pil_img.resize((PIZZA_PX, PIZZA_PX), Image.LANCZOS)
                self._slice_pil[(n, k)] = pil_full
                self._slice_photo[(n, k)] = ImageTk.PhotoImage(pil_full)
                self._slice_pil_plate[(n, k)] = pil_img.resize(
                    (PLATE_PIECE_PX, PLATE_PIECE_PX), Image.LANCZOS)

        # A full pizza at slice-count n, all n pieces merged into one
        # image up front (cutPizza always shows every piece, so this never
        # needs recomputing per-render).
        self._full_pizza_photo = {
            n: self._composite_photo(n, range(1, n + 1)) for n in range(1, 6)
        }

    def _composite_photo(self, n, ks):
        """Alpha-composite the given piece keys (for slice-count n) into
        one merged image and return it as a PhotoImage.

        Stacking separate Labels (one per piece, all at the same position)
        does NOT visually combine them: each Label's "transparent" pixels
        render as that Label's own opaque bg color, hiding whatever piece
        is stacked beneath it -- Tk doesn't composite sibling widgets'
        alpha channels. So pieces must be merged with real PIL alpha
        compositing into a single image before being displayed.
        """
        merged = Image.new("RGBA", (PIZZA_PX, PIZZA_PX), (0, 0, 0, 0))
        for k in ks:
            merged = Image.alpha_composite(merged, self._slice_pil[(n, k)])
        return ImageTk.PhotoImage(merged)

    @staticmethod
    def _random_plate_position():
        cx = cy = PLATE_PX / 2
        max_r = max(0.0, (PLATE_PX * PLATE_CIRCLE_FRACTION / 2) - (PLATE_PIECE_PX / 2))
        for _ in range(30):
            dx = random.uniform(-max_r, max_r)
            dy = random.uniform(-max_r, max_r)
            if dx * dx + dy * dy <= max_r * max_r:
                return cx + dx - PLATE_PIECE_PX / 2, cy + dy - PLATE_PIECE_PX / 2
        return cx - PLATE_PIECE_PX / 2, cy - PLATE_PIECE_PX / 2

    # ------------------------------------------------------------- build
    def _build(self):
        # Plain instruction text, packed first so it's the very top of the
        # window -- instruct() just swaps its text, nothing else.
        self.instruct_label = tk.Label(self.root, text="", bg=BG, fg=TEXT,
                                       font=("Helvetica", 16, "bold"))
        self.instruct_label.pack(side="top", pady=(12, 0))

        # Top-right "customers served" badge. Placed with place() (not
        # packed) so it floats independently in the corner regardless of
        # the packed layout beneath it -- same technique as snake_ui.py's
        # catch-count overlay.
        served_box = tk.Frame(self.root, bg=BUBBLE_BG,
                              highlightbackground=BUBBLE_BORDER, highlightthickness=2)
        self.served_label = tk.Label(served_box, text="Customers Served: 0",
                                     bg=BUBBLE_BG, fg=TEXT, font=("Helvetica", 13, "bold"),
                                     padx=10, pady=6)
        self.served_label.pack()
        served_box.place(relx=1.0, x=-16, y=16, anchor="ne")

        # Speech bubbles sit in their own row up top, roughly above their
        # own customer below; left_zone/right_zone (this row only) are what
        # _set_second_customer_visible toggles for the bubble half of the
        # second customer.
        bubbles_row = tk.Frame(self.root, bg=BG)
        bubbles_row.pack(fill="x", padx=16, pady=(10, 0))

        self.left_zone = tk.Frame(bubbles_row, bg=BG)
        self.left_zone.pack(side="left", fill="both", expand=True)
        self.right_zone = tk.Frame(bubbles_row, bg=BG)
        self.right_zone.pack(side="left", fill="both", expand=True)

        self.bubble1, self._bubble1_text = self._build_bubble(self.left_zone)
        self.bubble1.pack()
        self.bubble2, self._bubble2_text = self._build_bubble(self.right_zone)
        self.bubble2.pack()

        # The scene itself: customer1 and customer2 stand on either side of
        # the pizza/plate area (no overlap/compositing needed here, unlike
        # party_ui.py's server -- nothing here shares a position), each
        # next to their own pizzas. anchor="s" keeps everyone on one common
        # baseline.
        stage_row = tk.Frame(self.root, bg=BG)
        stage_row.pack(pady=(10, 0))

        tk.Label(stage_row, image=self._customer1_img, bg=BG).pack(side="left", anchor="s")
        self.pizza_col1 = tk.Frame(stage_row, bg=BG)
        self.pizza_col1.pack(side="left", padx=12, anchor="s")

        # customer2 + pizza_col2 are grouped in one frame so
        # _set_second_customer_visible can show/hide them as a unit.
        self.customer2_stage_col = tk.Frame(stage_row, bg=BG)
        self.customer2_stage_col.pack(side="left")
        self.pizza_col2 = tk.Frame(self.customer2_stage_col, bg=BG)
        self.pizza_col2.pack(side="left", padx=12, anchor="s")
        tk.Label(self.customer2_stage_col, image=self._customer2_img, bg=BG).pack(
            side="left", anchor="s")

        # Holds the dynamic Cut/Hand Over button, in normal top-down flow
        # right below the stage (so it sits a little below the Add Pizza
        # buttons at the bottom of each pizza column) -- NOT anchored to
        # the window's bottom edge the way side="bottom" packing on root
        # would be, so it stays close to the content above it.
        self.submit_row = tk.Frame(self.root, bg=BG)
        self.submit_row.pack(side="top", pady=(18, 10))

    def _build_bubble(self, parent):
        box = tk.Frame(parent, bg=BUBBLE_BG, highlightbackground=BUBBLE_BORDER,
                       highlightthickness=3)
        txt = tk.Text(box, bg=BUBBLE_BG, fg=TEXT, font=("Helvetica", 14, "bold"),
                     wrap="word", width=24, height=3, bd=0, highlightthickness=0,
                     cursor="arrow", state="disabled")
        txt.tag_configure("emphasis", font=("Helvetica", 18, "bold"),
                          foreground=EMPHASIS_COLOR, underline=True)
        txt.pack(padx=14, pady=10)
        return box, txt

    def _render_speech(self, txt_widget, text):
        # bySlice.py wraps a hint-level-2+ target value in UNDERLINE...
        # UNDERLINE (a terminal escape code that does nothing in a GUI) --
        # detect that marker and render the wrapped value with real visual
        # emphasis instead of displaying the raw escape characters.
        txt_widget.configure(state="normal")
        txt_widget.delete("1.0", "end")
        if UNDERLINE in text and text.count(UNDERLINE) >= 2:
            before, rest = text.split(UNDERLINE, 1)
            emphasized, after = rest.split(UNDERLINE, 1)
            txt_widget.insert("end", before)
            txt_widget.insert("end", emphasized, "emphasis")
            txt_widget.insert("end", after)
        else:
            txt_widget.insert("end", text)
        txt_widget.configure(state="disabled")

    def _set_second_customer_visible(self, visible):
        if visible:
            if not self.right_zone.winfo_ismapped():
                self.right_zone.pack(side="left", fill="both", expand=True)
            if not self.customer2_stage_col.winfo_ismapped():
                self.customer2_stage_col.pack(side="left")
        else:
            self.right_zone.pack_forget()
            self.customer2_stage_col.pack_forget()

    def _make_button(self, parent, text, command):
        lbl = tk.Label(parent, text=text, bg=BTN_BG, fg=TEXT, font=("Helvetica", 14, "bold"),
                       padx=14, pady=6, bd=4, relief="raised", cursor="hand2")
        lbl.bind("<Button-1>", lambda e: command())
        lbl.bind("<Enter>", lambda e: lbl.configure(bg=BTN_ACTIVE))
        lbl.bind("<Leave>", lambda e: lbl.configure(bg=BTN_BG))
        return lbl

    # ---------------------------------------------------------- instruct
    def instruct(self, text):
        """Set the plain instruction text shown at the top of the window."""
        if self._closed:
            return
        self.instruct_label.configure(text=text)
        self._show()

    def customerServed(self, n=1):
        """Bump the "Customers Served" badge -- call once per customer
        whose order came back correct (n=2 if crediting both customers of
        a double round at once)."""
        if self._closed:
            return
        self.customers_served += n
        self.served_label.configure(text=f"Customers Served: {self.customers_served}")
        self._show()

    # ------------------------------------------------------------- bubble
    def speak(self, text):
        if self._closed:
            return
        self._render_speech(self._bubble1_text, text)
        self._show()

    def speak2(self, text):
        if self._closed:
            return
        self._render_speech(self._bubble2_text, text)
        self._show()

    # ------------------------------------------------------------- cutPizza
    def makeCuts(self, denom2):
        if self._closed:
            return (1, None if denom2 is None else 1)

        self._set_second_customer_visible(denom2 is not None)
        # Only reset the cut/pizza-count/allowance state on the FIRST
        # makeCuts() call of a new round -- bySlice.py calls makeCuts()
        # again on every wrong guess too, and a mistake shouldn't wipe out
        # cuts or pizzas the player already had right. onPlate() marks
        # _pending_new_round True once the handover phase for this round
        # is under way, so the next fresh round's first makeCuts() call
        # still resets normally.
        if self._pending_new_round:
            self._cut_state = {"left": 1, "right": 1}
            self._cut_pizza_count = {"left": 1, "right": 1}
            self._pizza_added = {"left": False, "right": False}
            self._pending_new_round = False
            # Arm the handover phase to reset fresh too, once it starts.
            self._pending_new_handover = True
        active = ["left"] + (["right"] if denom2 is not None else [])

        for key in active:
            self._render_cut_pizza(key)

        submit = self._make_button(self.submit_row, "Cut", lambda: self._done.set(1))
        submit.pack()

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

        # A customer can have 2 pizzas here (after their own "Add Pizza"),
        # both always showing -- and cut to -- the SAME shared slice count:
        # clicking any one of them cycles all of that customer's pizzas
        # together, matching how they're a single combined answer.
        n = self._cut_state[key]
        pizzas_row = tk.Frame(col, bg=BG)
        pizzas_row.pack()
        for i in range(self._cut_pizza_count[key]):
            lbl = tk.Label(pizzas_row, image=self._full_pizza_photo[n], bg=BG, bd=0,
                           highlightthickness=0, cursor="hand2")
            lbl.grid(row=0, column=i, padx=6)
            lbl.bind("<Button-1>", lambda e, kk=key: self._cycle_pizza(kk))

        # Same one-time-ever-per-round allowance as handover's Add Pizza
        # (see _pizza_added) -- own button per customer, gone once used
        # here or in onPlate, in either order.
        if not self._pizza_added[key]:
            add_btn = self._make_button(col, "Add Pizza", lambda: self._add_cut_pizza(key))
            add_btn.pack(pady=(8, 0))

    def _cycle_pizza(self, key):
        if self._closed:
            return
        self._cut_state[key] = (self._cut_state[key] % 5) + 1
        self._render_cut_pizza(key)

    def _add_cut_pizza(self, key):
        if self._closed or self._pizza_added[key]:
            return
        self._pizza_added[key] = True
        self._cut_pizza_count[key] = 2
        self._render_cut_pizza(key)

    # ------------------------------------------------------------- handOver
    def onPlate(self, denom, denom2):
        if self._closed:
            return (0, None if denom2 is None else 0)

        self._set_second_customer_visible(denom2 is not None)
        # The cut phase for this round is over once handover starts -- the
        # next fresh round's first makeCuts() call should reset normally.
        self._pending_new_round = True
        active = ["left"] + (["right"] if denom2 is not None else [])

        # Only reset the plate and pizzas on the FIRST onPlate() call of a
        # new round -- bySlice.py calls onPlate() again on every wrong
        # guess too, and a mistake shouldn't wipe the plate, or the
        # pizzas, back to empty.
        if self._pending_new_handover:
            self._handover_denom = {"left": denom, "right": denom2}
            self._pizzas = {"left": [], "right": []}
            self._plate_count = {"left": 0, "right": 0}
            for key in active:
                # Carry the cut phase's pizza count forward -- a customer
                # who cut N pizzas there already has N pizzas here too,
                # instead of handover resetting back down to one and
                # making them re-click Add Pizza to get back to where
                # they left off.
                for _ in range(self._cut_pizza_count[key]):
                    self._new_pizza(key)
            self._pending_new_handover = False

        submit = self._make_button(self.submit_row, "Hand Over", lambda: self._done.set(1))
        submit.pack()

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
        if self._closed:
            return
        n = self._handover_denom[key]
        pieces = [{"k": k, "on_plate": False} for k in range(1, n + 1)]
        self._pizzas[key].append(pieces)
        self._render_handover(key)

    def _add_handover_pizza(self, key):
        # The Add Pizza button's own handler -- gated by the one-time
        # allowance, unlike the automatic initial _new_pizza(key) calls in
        # onPlate(), which always create that customer's first pizza.
        if self._closed or self._pizza_added[key]:
            return
        self._pizza_added[key] = True
        self._new_pizza(key)

    def _render_handover(self, key):
        col = self.pizza_col1 if key == "left" else self.pizza_col2
        for w in col.winfo_children():
            w.destroy()

        n = self._handover_denom[key]
        pizzas_row = tk.Frame(col, bg=BG)
        pizzas_row.pack()

        # Fixed PIZZAS_PER_ROW columns -- extra pizzas (Add Pizza) wrap to
        # another row instead of growing pizzas_row sideways, so the
        # window's width stays constant no matter how many get added.
        grid_idx = 0
        for pizza_idx, pieces in enumerate(self._pizzas[key]):
            remaining_ks = [p["k"] for p in pieces if not p["on_plate"]]
            if not remaining_ks:
                continue
            # Which pieces remain changes as they're clicked onto the
            # plate, so (unlike the full pizza in cutPizza) this can't be
            # precomputed -- composite fresh each render.
            composited = self._composite_photo(n, remaining_ks)
            lbl = tk.Label(pizzas_row, image=composited, bg=BG, bd=0,
                          highlightthickness=0, cursor="hand2")
            lbl.image = composited  # keep a reference alive, or it's GC'd
            r, c = divmod(grid_idx, PIZZAS_PER_ROW)
            lbl.grid(row=r, column=c, padx=6, pady=6)
            lbl.bind("<Button-1>",
                    lambda e, kk=key, pi=pizza_idx: self._pizza_piece_click(kk, pi, e.x, e.y))
            grid_idx += 1

        # Same one-time-ever-per-round allowance as the cut phase's Add
        # Pizza (see _pizza_added) -- gone once used here or during
        # makeCuts, in either order.
        if not self._pizza_added[key]:
            add_btn = self._make_button(col, "Add Pizza", lambda: self._add_handover_pizza(key))
            add_btn.pack(pady=(8, 0))

        plate_box = tk.Frame(col, bg=PLATE_BG, highlightbackground=BUBBLE_BORDER,
                             highlightthickness=2)
        plate_box.pack(pady=(10, 0))

        # Composite every plated piece directly onto a copy of the plate
        # art (same technique as the pizza: separate stacked widgets don't
        # blend transparency against each other, so the pieces have to be
        # merged into one image to actually look like they're on the
        # plate rather than floating in front of it).
        plate_img = self._plate_pil.copy()
        for pieces in self._pizzas[key]:
            for piece in pieces:
                if piece["on_plate"]:
                    piece_img = self._slice_pil_plate[(n, piece["k"])]
                    pos = (round(piece["plate_x"]), round(piece["plate_y"]))
                    plate_img.paste(piece_img, pos, piece_img)
        plate_photo = ImageTk.PhotoImage(plate_img)

        plate_lbl = tk.Label(plate_box, image=plate_photo, bg=PLATE_BG, bd=0,
                             highlightthickness=0, cursor="hand2")
        plate_lbl.image = plate_photo  # keep a reference alive, or it's GC'd
        plate_lbl.pack()
        plate_lbl.bind("<Button-1>", lambda e, kk=key: self._plate_click(kk, e.x, e.y))

    def _pizza_piece_click(self, key, pizza_idx, x, y):
        if self._closed:
            return
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
                piece["plate_x"], piece["plate_y"] = self._random_plate_position()
                self._plate_count[key] += 1
                self._render_handover(key)
                return

    def _plate_click(self, key, x, y):
        if self._closed:
            return
        n = self._handover_denom[key]
        # Later-placed pieces were composited last (on top), so check them
        # first for click priority where pieces overlap -- track candidates
        # in placement order and take the last (topmost) match.
        hit = None
        for pizza_idx, pieces in enumerate(self._pizzas[key]):
            for piece_idx, piece in enumerate(pieces):
                if not piece["on_plate"]:
                    continue
                # Match the rounded position _render_handover actually
                # pastes the piece at, or hit-testing can land on the
                # wrong pixel by up to 1px versus what's on screen.
                px, py = round(piece["plate_x"]), round(piece["plate_y"])
                local_x, local_y = x - px, y - py
                if 0 <= local_x < PLATE_PIECE_PX and 0 <= local_y < PLATE_PIECE_PX:
                    pil_img = self._slice_pil_plate[(n, piece["k"])]
                    if pil_img.getpixel((local_x, local_y))[3] > 10:
                        hit = (pizza_idx, piece_idx)
        if hit is not None:
            pizza_idx, piece_idx = hit
            piece = self._pizzas[key][pizza_idx][piece_idx]
            piece["on_plate"] = False
            del piece["plate_x"], piece["plate_y"]
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
