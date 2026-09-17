# Slice UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `slice_ui.py` so `bySlice.py` runs end-to-end: a two-customer (or one-customer) pizza-fraction game where the player cuts a pizza into the right number of slices, then hands the right number of them over on a plate.

**Architecture:** One persistent `tk.Tk()` window (matching `party_ui.py`/`coin_ui.py`/`grocery_ui.py`'s reuse-across-rounds pattern), with a `SliceUI` class holding two symmetric customer columns (left = "1"/no-suffix methods, right = "2"-suffix methods) sharing a counter. Each pizza is rendered as a stack of same-size, same-position `Label`s (one per slice-image piece) so pieces visually combine into a whole pizza via their transparent backgrounds; during handover, which piece a click actually hit is determined by testing each piece's real pixel alpha at the click point (top piece first), not by widget bounding boxes, since every piece's bounding box covers the entire pizza.

**Tech Stack:** Python 3, Tkinter, Pillow (PIL) — same as the rest of this project. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-17-slice-ui-design.md`

## Global Constraints

- Follow the visual style already established in `party_ui.py`/`coin_ui.py`/`grocery_ui.py`: warm palette (`BG = "#fdf6e3"`, `TEXT = "#3b2f1e"`), `tk.Label` styled as buttons (not `tk.Button`), Pillow for all image loading (`Image.open(path).convert("RGBA")`), one persistent `tk.Tk()` reused across every call.
- Slice image filenames use an **uppercase** `.PNG` extension (`sliceimages/1slice.PNG`, `sliceimages/3slice-2.PNG`, etc.) — unlike the rest of the project's lowercase `.png`. Get this exactly right or image loading fails.
- The counter (`counter.png`) and the handover plate (`plate.png.webp`) are reused from `partyimages/`, not `sliceimages/`.
- `denom2`/`numer2` (and therefore `slice2`/`slices2`) are `None` whenever there's only one customer. Never invent a value for a customer that doesn't exist — return `None` for that slot exactly.
- No automated test suite (matches every other `*_ui.py` in this project, and is an explicit non-goal in the spec). Verification is manual: each task includes a throwaway smoke script (write it under the scratchpad directory, run it, confirm the described behaviors via direct method calls / widget introspection since this environment has no guaranteed real display, then delete the script — do not commit it).
- Do not modify `bySlice.py` — it's already correct (verified: parses cleanly, all previously-found bugs fixed) and its calls (`speak`, `speak2`, `makeCuts(denom2)`, `onPlate(denom, denom2)`) are exactly what `SliceUI` must implement.
- No cross-round or cross-retry state persistence: every `makeCuts`/`onPlate` call starts fresh (pizzas reset to 1 slice / a freshly-cut pizza with nothing on the plate).

---

## File Structure

- **Create:** `slice_ui.py` — the `SliceUI` class implementing the full `bySlice.py`-facing interface. Single file (matches the project's convention of one file per game UI — `coin_ui.py`, `grocery_ui.py`, `party_ui.py` are each one file).

## Task 1: `SliceUI` window skeleton, images, and speech bubbles

**Files:**
- Create: `slice_ui.py`

**Interfaces:**
- Produces: `SliceUI(image_dir="sliceimages")` with a persistent `self.root`, `self.pizza_col1`/`self.pizza_col2` (empty containers later tasks render pizzas into), `self._slice_photo[(n, k)]` / `self._slice_pil[(n, k)]` / `self._slice_photo_small[(n, k)]` (loaded slice-piece images, for n in 1..5, k in 1..n), `self._make_button(parent, text, command)`, `self._show()`, `self.speak(text)`, `self.speak2(text)`, `.close()`.

- [ ] **Step 1: Write `slice_ui.py`**

```python
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
```

- [ ] **Step 2: Write a throwaway smoke script**

Write to `<scratchpad>/smoke_skeleton.py` (not committed):

```python
import sys
sys.path.insert(0, "/Users/jessicaguo/Downloads/nerdygame")
from slice_ui import SliceUI

ui = SliceUI()
ui.speak("I'd like 3/4 pizza")
ui.speak2("I'd like 1/2 pizza")
ui.root.update_idletasks()
print("slice_pil keys count (expect 1+2+3+4+5=15):", len(ui._slice_pil))
print("bubble1 text:", ui._bubble1_text.cget("text"))
print("bubble2 text:", ui._bubble2_text.cget("text"))
print("window size:", ui.root.winfo_width(), ui.root.winfo_height())
ui.root.after(500, ui.root.quit)
ui._show()
ui.root.mainloop()
```

- [ ] **Step 3: Run it and manually verify**

Run: `python3 <scratchpad>/smoke_skeleton.py`

Verify:
- No exceptions loading images (especially the uppercase `.PNG` slice files and the `partyimages/plate.png.webp` reuse).
- `len(ui._slice_pil)` prints `15` (1 + 2 + 3 + 4 + 5 pieces across slice-counts 1..5).
- Both bubble texts print correctly.
- If a real display is available, confirm visually: customer1 on the far left, customer2 on the far right, counter spanning the bottom, both speech bubbles showing their text, both pizza columns empty (nothing rendered there yet — that's Task 2/3).

- [ ] **Step 4: Delete the smoke script and commit**

```bash
rm <scratchpad>/smoke_skeleton.py
cd /Users/jessicaguo/Downloads/nerdygame
git add slice_ui.py
git commit -m "Add SliceUI window skeleton with images and speech bubbles"
```

## Task 2: `makeCuts` (cutPizza phase)

**Files:**
- Modify: `slice_ui.py`

**Interfaces:**
- Consumes: `self.pizza_col1`/`self.pizza_col2`, `self._slice_photo`, `self._make_button`, `self._done`, `self._show()` (Task 1).
- Produces: `SliceUI.makeCuts(denom2) -> (slice1, slice2)`.

- [ ] **Step 1: Add the cutPizza methods**

Add to `slice_ui.py` (after `speak2`):

```python
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
        submit.destroy()

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
```

- [ ] **Step 2: Write a throwaway smoke script**

Write to `<scratchpad>/smoke_cutpizza.py` (not committed):

```python
import sys
sys.path.insert(0, "/Users/jessicaguo/Downloads/nerdygame")
from slice_ui import SliceUI

ui = SliceUI()

def submit_soon():
    ui.root.after(150, lambda: ui._done.set(1))

def check_and_submit_double():
    print("cut_state before clicks:", ui._cut_state)
    # cycle left pizza 3 times (1->2->3->4), right pizza once (1->2)
    for _ in range(3):
        ui._cycle_pizza("left")
    ui._cycle_pizza("right")
    print("cut_state after clicks:", ui._cut_state)
    # test wraparound: cycle left 2 more times (4->5->1)
    ui._cycle_pizza("left")
    ui._cycle_pizza("left")
    print("cut_state after wraparound (left should be 1):", ui._cut_state)
    ui._cycle_pizza("left")  # back to 2 for a clean submit value
    submit_soon()

ui.root.after(80, check_and_submit_double)
result = ui.makeCuts(3)  # double customer
print("makeCuts(3) result:", result)

def check_single():
    print("pizza_col2 children (should be empty):", len(ui.pizza_col2.winfo_children()))
    ui._reset_pizza("left")
    ui._cycle_pizza("left")
    submit_soon()

ui.root.after(80, check_single)
result2 = ui.makeCuts(None)  # single customer
print("makeCuts(None) result (slice2 should be None):", result2)

ui.root.after(50, ui.root.quit)
ui.root.mainloop()
```

- [ ] **Step 3: Run it and manually verify**

Run: `python3 <scratchpad>/smoke_cutpizza.py`

Verify:
- `makeCuts(3)` result is `(2, 2)` (left cycled 1->2->3->4->5->1->2, right cycled 1->2).
- Wraparound printed correctly: after 5 total cycles from 1, left is back to `1`.
- `pizza_col2` has 0 children when `denom2 is None`.
- `makeCuts(None)` result is `(1, None)` — confirms the single-customer contract (`slice2` is exactly `None`, not `0`).
- No traceback on close.

- [ ] **Step 4: Delete the smoke script and commit**

```bash
rm <scratchpad>/smoke_cutpizza.py
cd /Users/jessicaguo/Downloads/nerdygame
git add slice_ui.py
git commit -m "Implement makeCuts (cutPizza) with click-to-cycle and New Pizza reset"
```

## Task 3: `onPlate` (handOver phase, single pizza per customer)

**Files:**
- Modify: `slice_ui.py`

**Interfaces:**
- Consumes: `self.pizza_col1`/`self.pizza_col2`, `self._slice_photo`/`self._slice_pil`/`self._slice_photo_small`, `self._plate_img`, `self._make_button`, `self._done`, `self._show()` (Task 1).
- Produces: `SliceUI.onPlate(denom, denom2) -> (slices1, slices2)`. Internal per-customer pizza list (`self._pizzas[key]`, a list of pizzas, each a list of `{"k": int, "on_plate": bool}` piece dicts) is introduced now but only ever holds one pizza per customer in this task — Task 4 adds the "Add Pizza" button that can grow it.

- [ ] **Step 1: Add the handOver methods**

Add to `slice_ui.py` (after `_reset_pizza`):

```python
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
        submit.destroy()

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
```

- [ ] **Step 2: Write a throwaway smoke script**

Write to `<scratchpad>/smoke_handover.py` (not committed):

```python
import sys
sys.path.insert(0, "/Users/jessicaguo/Downloads/nerdygame")
from slice_ui import SliceUI, PIZZA_PX

ui = SliceUI()

def click_pieces_and_submit():
    n = ui._handover_denom["left"]
    print("left pizza has", n, "pieces; plate count starts at", ui._plate_count["left"])
    # click at the exact center of the pizza repeatedly; each click should
    # find *some* opaque piece there (pizza center is opaque in every
    # piece) and move exactly one piece to the plate per click, in some
    # order, until all n are gone.
    cx = cy = PIZZA_PX // 2
    for _ in range(n):
        before = ui._plate_count["left"]
        ui._pizza_piece_click("left", 0, cx, cy)
        after = ui._plate_count["left"]
        print("click at center: plate count", before, "->", after)
    print("final plate count (expect == n):", ui._plate_count["left"], "== ", n)
    # move one back
    ui._plate_piece_click("left", 0, 0)
    print("after moving one back:", ui._plate_count["left"])
    ui.root.after(150, lambda: ui._done.set(1))

ui.root.after(80, click_pieces_and_submit)
result = ui.onPlate(4, None)
print("onPlate(4, None) result:", result, "(slices2 should be None)")
ui.root.after(50, ui.root.quit)
ui.root.mainloop()
```

- [ ] **Step 3: Run it and manually verify**

Run: `python3 <scratchpad>/smoke_handover.py`

Verify:
- Clicking the exact pizza center `n` times moves exactly one piece to the plate each time (the alpha hit-test finds a real piece there every time — the center of a pie wedge image is always opaque), ending with `plate_count == n`.
- Moving one piece back via `_plate_piece_click` decrements the count correctly.
- Final `onPlate(4, None)` result is `(4, None)` — the single-customer contract holds here too.
- No traceback on close.

- [ ] **Step 4: Delete the smoke script and commit**

```bash
rm <scratchpad>/smoke_handover.py
cd /Users/jessicaguo/Downloads/nerdygame
git add slice_ui.py
git commit -m "Implement onPlate (handOver) with alpha-tested click-to-plate"
```

## Task 4: "Add Pizza" button (multi-pizza-per-customer)

**Files:**
- Modify: `slice_ui.py`

**Interfaces:**
- Consumes: `self._pizzas`, `self._new_pizza`, `self._render_handover` (Task 3).
- Produces: an "Add Pizza" button rendered per customer during `onPlate`, calling the existing `self._new_pizza(key)` (already able to append an additional pizza — Task 3 built it generically, this task just exposes it as a button and confirms multi-pizza rendering/clicking works end to end).

- [ ] **Step 1: Add the button**

In `slice_ui.py`, inside `_render_handover`, add the button right after the `pizzas_row` loop (before the `plate_box` section):

```python
        add_btn = self._make_button(col, "Add Pizza", lambda: self._new_pizza(key))
        add_btn.pack(pady=(8, 0))
```

The full method should now read (only the addition shown — insert it between the `pizzas_row` for-loop and the `plate_box = tk.Frame(...)` line):

```python
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
```

- [ ] **Step 2: Write a throwaway smoke script**

Write to `<scratchpad>/smoke_addpizza.py` (not committed):

```python
import sys
sys.path.insert(0, "/Users/jessicaguo/Downloads/nerdygame")
from slice_ui import SliceUI, PIZZA_PX

ui = SliceUI()

def exercise():
    print("pizzas for left after first render (expect 1):", len(ui._pizzas["left"]))
    ui._new_pizza("left")  # simulates clicking "Add Pizza"
    print("pizzas for left after Add Pizza (expect 2):", len(ui._pizzas["left"]))

    # move all of pizza 0's pieces and 2 of pizza 1's pieces to the plate
    # (denom=3, numer=5 scenario: need slices from a 2nd pizza)
    cx = cy = PIZZA_PX // 2
    for _ in range(3):
        ui._pizza_piece_click("left", 0, cx, cy)
    for _ in range(2):
        ui._pizza_piece_click("left", 1, cx, cy)
    print("plate count (expect 5):", ui._plate_count["left"])

    ui.root.after(150, lambda: ui._done.set(1))

ui.root.after(80, exercise)
result = ui.onPlate(3, None)
print("onPlate(3, None) result (expect (5, None)):", result)
ui.root.after(50, ui.root.quit)
ui.root.mainloop()
```

- [ ] **Step 3: Run it and manually verify**

Run: `python3 <scratchpad>/smoke_addpizza.py`

Verify:
- After the initial `onPlate` call, `left` has exactly 1 pizza.
- After simulating "Add Pizza", `left` has 2 pizzas, both cut into `denom` (3) pieces.
- Moving pieces from *both* pizzas onto the same plate correctly sums into one `_plate_count` (final result `(5, None)`), confirming pieces from any of a customer's pizzas land on that customer's single shared plate.
- No traceback on close.

- [ ] **Step 4: Delete the smoke script and commit**

```bash
rm <scratchpad>/smoke_addpizza.py
cd /Users/jessicaguo/Downloads/nerdygame
git add slice_ui.py
git commit -m "Add 'Add Pizza' button for improper-fraction handover"
```

## Task 5: Full end-to-end verification

**Files:**
- Modify (if issues found): `slice_ui.py`

**Interfaces:**
- Consumes: the complete `SliceUI` surface from Tasks 1-4 as called by the unmodified `bySlice.py`.
- Produces: a confirmed-working run of `bySlice.py`'s full flow (both single- and double-customer rounds, both phases).

- [ ] **Step 1: Write and run a headless driver through the real bySlice.py functions**

`bySlice.py` calls `serveCustomers(...)` at import time only if invoked directly — check the bottom of the file for how it's actually run (it may need a manual call). Since this sandbox likely has no real display (confirmed by every prior `*_ui.py` build in this project), write a throwaway driver in your scratchpad that imports `bySlice`'s `cutPizza`/`handOver` functions directly and drives `SliceUI` the same way Task 2-4's smoke scripts did (schedule `ui.root.after(...)` callbacks that click pieces/press buttons *before* each blocking call, since `makeCuts`/`onPlate` block via `wait_variable`). Exercise, using the real `cutPizza`/`handOver` functions (not reimplementations of their logic):
- A double-customer round: both pizzas cut correctly on the first or second try (to see the hint/retry path exercise `ui.speak`/`ui.speak2` at least once), then handed over correctly (including one customer needing "Add Pizza" for an improper fraction, i.e. pick `numer > denom` for at least one test round).
- A single-customer round: confirm the right pizza column / plate area stays empty throughout, and `slice2`/`slices2` are `None` both times.

- [ ] **Step 2: Fix any issues found**

If any exception, hang, or logic mismatch turns up, fix it directly in `slice_ui.py` (do not modify `bySlice.py`) and re-run Step 1 until the full flow verifies cleanly.

- [ ] **Step 3: Commit**

```bash
cd /Users/jessicaguo/Downloads/nerdygame
git add slice_ui.py
git commit -m "Fix issues found in end-to-end slice UI verification"
```

(Skip this commit if Step 2 required no changes.)
