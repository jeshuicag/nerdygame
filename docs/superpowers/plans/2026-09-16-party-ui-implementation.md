# Party UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `party_ui.py` (and a new `placement_board.py`) so `bdayparty.py` runs end-to-end with a Tkinter+PIL frontend: a server speech bubble, a checklist/shopping-list/number-answer widget per phase, and an optional full-screen pizza/plate placement visual that carries state across phases.

**Architecture:** One persistent `tk.Tk()` window (matching `coin_ui.py`/`grocery_ui.py`'s reuse-across-rounds pattern) with a `PartyUI` class holding all phase logic, plus a standalone `PlacementBoard` class (new file) implementing the generic clickable base+inventory visual shared by the pizza-topping builder and the cupcake-plate builder. `PlacementBoard` separates plain-Python state (`placements`, `inventory`, `active_item`) from its Tk rendering (`render(switcher_parent, bases_parent)`), so `PartyUI` can destroy and rebuild surrounding widgets each call while the board's own data — and therefore its on-screen state — survives across calls.

**Tech Stack:** Python 3, Tkinter, Pillow (PIL) — same as `coin_ui.py`/`grocery_ui.py`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-16-party-ui-design.md`

## Global Constraints

- Follow the visual style already established in `coin_ui.py`/`grocery_ui.py`: warm palette (`BG = "#fdf6e3"`, `TEXT = "#3b2f1e"`), `tk.Label` styled as buttons (not `tk.Button`, which ignores colors on macOS Tk 8.5), Pillow for all PNG/WebP loading (`Image.open(path).convert("RGBA")`), one persistent `tk.Tk()` reused across every call.
- `toppings` order is fixed by `bdayparty.py`: `["pineapple", "onion", "olive", "bellpepper", "mushroom", "pepperoni"]`, with topping images in `shopimages/<name>.png`.
- `t_inv`/`tpk`/`mistakes`/`warnings` are parallel lists indexed by topping; `mistakes[i] % 2 == 0` (and `!= -1`) means topping `i` is already correct, `warnings[i] == 0` means the buy amount for topping `i` is already correct.
- The pizza/plate visual's working inventory is a visualization aid only — it is never read back as the player's submitted answer; the player fills in the checklist/shopping-list/number field themselves.
- No automated test suite (matches the existing `coin_ui.py`/`grocery_ui.py` convention, and is an explicit non-goal in the spec). Verification is manual: each task includes a throwaway smoke script (write it under the scratchpad directory, run it, interact with the window, confirm the described behaviors, then delete the script — do not commit it). If no display is available in the execution environment, at minimum run `python3 -c "import party_ui"` / `import placement_board` to confirm there are no import/syntax errors, and flag to the user that visual confirmation still needs to happen on a machine with a display before the task is considered fully done.
- Do not modify `bdayparty.py`'s game logic, randomization, or the `PartyUI` method signatures it already calls (`server`, `display`, `askEnough`, `prompt`, `quest`).

---

## File Structure

- **Create:** `placement_board.py` — the generic `PlacementBoard` class (pizza-base / plate visual, item placement state + rendering). No dependency on `party_ui.py`.
- **Modify:** `party_ui.py` — the `PartyUI` class implementing the full backend-facing interface, importing and using `PlacementBoard`.

## Task 1: `PlacementBoard` component

**Files:**
- Create: `placement_board.py`

**Interfaces:**
- Produces: `PlacementBoard(base_image_path: str, items: list[tuple[str, str]], base_count: int, initial_inventory: dict[str, int], show_item_switcher: bool = True)` with `.render(switcher_parent: tk.Widget, bases_parent: tk.Widget) -> None`, and public data attributes `.placements: list[list[str]]` (one list per base, in click order) and `.inventory: dict[str, int]` (working copy, mutated by clicks).

- [ ] **Step 1: Write `placement_board.py`**

```python
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
```

- [ ] **Step 2: Write a throwaway smoke script**

Write to `<scratchpad>/smoke_board.py` (not committed):

```python
import sys
sys.path.insert(0, "/Users/jessicaguo/Downloads/nerdygame")

import tkinter as tk
from placement_board import PlacementBoard

root = tk.Tk()
switcher = tk.Frame(root)
switcher.pack(pady=10)
bases = tk.Frame(root)
bases.pack(pady=10)

items = [
    ("pineapple", "/Users/jessicaguo/Downloads/nerdygame/shopimages/pineapple.png"),
    ("onion", "/Users/jessicaguo/Downloads/nerdygame/shopimages/onion.png"),
]
board = PlacementBoard(base_image_path="/Users/jessicaguo/Downloads/nerdygame/partyimages/pizza.png",
                       items=items, base_count=3,
                       initial_inventory={"pineapple": 4, "onion": 2},
                       show_item_switcher=True)
board.render(switcher, bases)
root.mainloop()
```

- [ ] **Step 3: Run it and manually verify**

Run: `python3 <scratchpad>/smoke_board.py`

Verify:
- Pineapple icon starts with a green "active" border; clicking the onion icon moves the active border to onion.
- Clicking a pizza base while pineapple is active places a small pineapple icon on it and the pineapple count next to its switcher icon drops by 1.
- Clicking that placed pineapple icon removes it and the count goes back up by 1.
- Clicking a base when the active item's inventory count is 0 does nothing (no placement, no crash).
- Closing the window does not raise a traceback.

- [ ] **Step 4: Delete the smoke script and commit**

```bash
rm <scratchpad>/smoke_board.py
cd /Users/jessicaguo/Downloads/nerdygame
git add placement_board.py
git commit -m "Add generic PlacementBoard for pizza/plate placement visuals"
```

## Task 2: `PartyUI` window skeleton

**Files:**
- Modify: `party_ui.py`

**Interfaces:**
- Consumes: nothing from Task 1 yet (import added but unused until Task 6/7).
- Produces: `PartyUI(image_dir="partyimages", toppings_dir="shopimages")` with a persistent `self.root`, `self.bubble_frame`/`self.bubble_text`/`self.bubble_toppings`, `self.middle_frame` containing `self.plain_panel` and `self.visual_frame` (the latter containing `self.top_inventory_frame`, and a row of `self.left_panel_frame` / `self.center_board_frame` / `self.right_panel_frame`), `self.backdrop_frame`/`self.counter_label`/`self.server_label`, `self._set_backdrop_dim(dimmed: bool)`, `self._show()`, `.close()`.

- [ ] **Step 1: Write the skeleton**

Replace `party_ui.py` with:

```python
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

from party_ui import PartyUI

ui = PartyUI()
ui._show()
ui.root.after(3000, lambda: ui._set_backdrop_dim(True))
ui.root.after(6000, lambda: ui._set_backdrop_dim(False))
ui.root.mainloop()
```

- [ ] **Step 3: Run it and manually verify**

Run: `python3 <scratchpad>/smoke_skeleton.py`

Verify:
- Window opens centered, showing an empty white-bordered speech bubble at top, blank middle area, and the counter spanning most of the window width at the bottom with the server sprite to its left (server's lower half should be covered by/behind the counter graphic — if it looks wrong, adjust the `padx`/pack order of `server_label`/`counter_label` in `_build`).
- After 3 seconds the counter/server visibly shrink and fade (dimmed state); after 6 seconds they return to normal.
- Closing the window does not raise a traceback.

- [ ] **Step 4: Delete the smoke script and commit**

```bash
rm <scratchpad>/smoke_skeleton.py
cd /Users/jessicaguo/Downloads/nerdygame
git add party_ui.py
git commit -m "Add PartyUI window skeleton with bubble, middle zone, and backdrop"
```

## Task 3: Speech bubble (`server`/`display`)

**Files:**
- Modify: `party_ui.py`

**Interfaces:**
- Consumes: `self.bubble_text`, `self.bubble_toppings`, `self.toppings_dir`, `self._show()` from Task 2.
- Produces: `PartyUI.server(text: str, tpk: list[int] | None, toppings: list[str] | None) -> None`, `PartyUI.display(text: str, a, b) -> None`, `PartyUI._topping_icon(name: str) -> ImageTk.PhotoImage`.

- [ ] **Step 1: Add the bubble methods**

Add to `party_ui.py` (inside `PartyUI`, after `_make_button`):

```python
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
        self._render_bubble(text, tpk, toppings)

    def display(self, text, a, b):
        self._render_bubble(text, None, None)
```

- [ ] **Step 2: Write a throwaway smoke script**

Write to `<scratchpad>/smoke_bubble.py` (not committed):

```python
import sys
sys.path.insert(0, "/Users/jessicaguo/Downloads/nerdygame")

from party_ui import PartyUI

ui = PartyUI()
ui.server("Order up! We have a party with 4 kids.", [3, 5],
          ["pineapple", "onion"])
ui.root.after(3000, lambda: ui.display("Pizzas going out! But what's a party without cake?", None, None))
ui.root.mainloop()
```

- [ ] **Step 3: Run it and manually verify**

Run: `python3 <scratchpad>/smoke_bubble.py`

Verify:
- Bubble shows the order text plus two rows: a pineapple icon with "x3" and an onion icon with "x5".
- After 3 seconds the bubble switches to the cupcake text with no icon rows underneath (and the old icon rows are gone, not left over).

- [ ] **Step 4: Delete the smoke script and commit**

```bash
rm <scratchpad>/smoke_bubble.py
cd /Users/jessicaguo/Downloads/nerdygame
git add party_ui.py
git commit -m "Implement server/display speech bubble rendering"
```

## Task 4: Checklist (`askEnough`, plain mode)

**Files:**
- Modify: `party_ui.py`

**Interfaces:**
- Consumes: `self.plain_panel`, `self._make_button`, `self._topping_icon`, `self._checklist_state`, `self._done`, `self._show()`.
- Produces: `PartyUI.askEnough(num_kids, tpk, t_inv, mistakes, toppings, allow_pizza_visual) -> list[int]` (visual branch raises `NotImplementedError` until Task 6), `PartyUI._render_checklist_panel(parent, t_inv, mistakes, toppings) -> dict[int, tk.BooleanVar]`, `PartyUI._collect_checklist(check_vars, mistakes, toppings) -> list[int]`.

- [ ] **Step 1: Add the checklist methods**

Add to `party_ui.py`:

```python
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
            if mistakes[i] % 2 == 0 and mistakes[i] != -1:
                enough.append(1 if self._checklist_state.get(i, False) else 0)
            else:
                val = check_vars[i].get()
                self._checklist_state[i] = val
                enough.append(1 if val else 0)
        return enough

    def askEnough(self, num_kids, tpk, t_inv, mistakes, toppings, allow_pizza_visual):
        self._num_kids = num_kids
        if allow_pizza_visual:
            return self._ask_enough_visual(t_inv, mistakes, toppings, tpk)
        return self._ask_enough_plain(t_inv, mistakes, toppings)

    def _ask_enough_plain(self, t_inv, mistakes, toppings):
        self._set_backdrop_dim(False)
        self.visual_frame.pack_forget()
        self.plain_panel.pack(fill="both", expand=True)

        check_vars = self._render_checklist_panel(self.plain_panel, t_inv, mistakes, toppings)

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)
        return self._collect_checklist(check_vars, mistakes, toppings)

    def _ask_enough_visual(self, t_inv, mistakes, toppings, tpk):
        raise NotImplementedError("pizza visual wired up in Task 6")
```

- [ ] **Step 2: Write a throwaway smoke script**

Write to `<scratchpad>/smoke_checklist.py` (not committed):

```python
import sys
sys.path.insert(0, "/Users/jessicaguo/Downloads/nerdygame")

from party_ui import PartyUI

ui = PartyUI()
toppings = ["pineapple", "onion"]

def round1():
    result = ui.askEnough(2, [3, 5], [10, 2], [-1, -1], toppings, False)
    print("round1 result:", result)
    ui.root.after(200, round2)

def round2():
    # simulate: pineapple was answered correctly (mistake 0), onion still wrong (mistake 3)
    result = ui.askEnough(2, [3, 5], [10, 2], [0, 3], toppings, False)
    print("round2 result:", result)

ui.root.after(500, round1)
ui.root.mainloop()
```

- [ ] **Step 3: Run it and manually verify**

Run: `python3 <scratchpad>/smoke_checklist.py`

Verify:
- Round 1: both rows editable; check the pineapple box, leave onion unchecked, click Submit; printed result is `[1, 0]`.
- Round 2: pineapple row is dimmed/disabled and pre-checked (matches what was submitted in round 1); onion row is still editable and unchecked; check it and Submit; printed result is `[1, 1]`.
- No traceback on close.

- [ ] **Step 4: Delete the smoke script and commit**

```bash
rm <scratchpad>/smoke_checklist.py
cd /Users/jessicaguo/Downloads/nerdygame
git add party_ui.py
git commit -m "Implement plain-mode checklist for askEnough"
```

## Task 5: Shopping list (`prompt`, plain mode)

**Files:**
- Modify: `party_ui.py`

**Interfaces:**
- Consumes: `self.plain_panel`, `self._make_button`, `self._topping_icon`, `self._shoplist_state`, `self._done`, `self._show()`.
- Produces: `PartyUI.prompt(kids, tpk, t_inv, mistakes, warnings, toppings, allow_pizza_visual) -> list[int]` (visual branch raises `NotImplementedError` until Task 6), `PartyUI._render_shoplist_panel(parent, mistakes, warnings, toppings) -> dict[int, tk.Entry]`, `PartyUI._collect_shoplist(entries, mistakes, warnings, toppings) -> list[int]`.

- [ ] **Step 1: Add the shopping-list methods**

Add to `party_ui.py`:

```python
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
        self._num_kids = kids
        if allow_pizza_visual:
            return self._prompt_visual(t_inv, mistakes, warnings, toppings, tpk)
        return self._prompt_plain(mistakes, warnings, toppings)

    def _prompt_plain(self, mistakes, warnings, toppings):
        self._set_backdrop_dim(False)
        self.visual_frame.pack_forget()
        self.plain_panel.pack(fill="both", expand=True)

        entries = self._render_shoplist_panel(self.plain_panel, mistakes, warnings, toppings)

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)
        return self._collect_shoplist(entries, mistakes, warnings, toppings)

    def _prompt_visual(self, t_inv, mistakes, warnings, toppings, tpk):
        raise NotImplementedError("pizza visual wired up in Task 6")
```

- [ ] **Step 2: Write a throwaway smoke script**

Write to `<scratchpad>/smoke_shoplist.py` (not committed):

```python
import sys
sys.path.insert(0, "/Users/jessicaguo/Downloads/nerdygame")

from party_ui import PartyUI

ui = PartyUI()
toppings = ["pineapple", "onion", "olive"]
# pineapple/olive need restock (mistake 2/3); onion already had enough (mistake 0, hidden)
mistakes = [2, 0, 3]

def round1():
    result = ui.prompt(2, [3, 5, 1], [1, 10, 0], mistakes, [-1, -1, -1], toppings, False)
    print("round1 result:", result)
    ui.root.after(200, round2)

def round2():
    # simulate: pineapple amount now correct (warnings[0]=0), olive still wrong (warnings[2]=2)
    result = ui.prompt(2, [3, 5, 1], [1, 10, 0], mistakes, [0, -1, 2], toppings, False)
    print("round2 result:", result)

ui.root.after(500, round1)
ui.root.mainloop()
```

- [ ] **Step 3: Run it and manually verify**

Run: `python3 <scratchpad>/smoke_shoplist.py`

Verify:
- Round 1: only pineapple and olive rows appear (onion hidden, mistake 0), both editable text fields defaulting to "0"; type "5" for pineapple, "2" for olive, Submit; printed result is `[5, 0, 2]`.
- Round 2: pineapple row is now locked/dimmed showing "5" as static text; olive row is still editable; type "3" for olive, Submit; printed result is `[5, 0, 3]`.
- No traceback on close.

- [ ] **Step 4: Delete the smoke script and commit**

```bash
rm <scratchpad>/smoke_shoplist.py
cd /Users/jessicaguo/Downloads/nerdygame
git add party_ui.py
git commit -m "Implement plain-mode shopping list for prompt"
```

## Task 6: Pizza visual wiring + cross-phase carryover

**Files:**
- Modify: `party_ui.py`

**Interfaces:**
- Consumes: `PlacementBoard` (Task 1), `self.top_inventory_frame`/`self.center_board_frame`/`self.left_panel_frame`/`self.right_panel_frame`/`self.visual_frame`/`self.plain_panel` (Task 2), `self._render_checklist_panel`/`self._collect_checklist` (Task 4), `self._render_shoplist_panel`/`self._collect_shoplist` (Task 5).
- Produces: `PartyUI._get_pizza_board(t_inv, toppings) -> PlacementBoard` (memoized on `self._pizza_board`), `PartyUI._render_order_list(tpk, toppings) -> None`, working `_ask_enough_visual`/`_prompt_visual`.

- [ ] **Step 1: Replace the `NotImplementedError` stubs**

In `party_ui.py`, add this new method and replace the two stub methods from Tasks 4 and 5:

```python
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
```

Replace:

```python
    def _ask_enough_visual(self, t_inv, mistakes, toppings, tpk):
        raise NotImplementedError("pizza visual wired up in Task 6")
```

with:

```python
    def _ask_enough_visual(self, t_inv, mistakes, toppings, tpk):
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
        return self._collect_checklist(check_vars, mistakes, toppings)
```

Replace:

```python
    def _prompt_visual(self, t_inv, mistakes, warnings, toppings, tpk):
        raise NotImplementedError("pizza visual wired up in Task 6")
```

with:

```python
    def _prompt_visual(self, t_inv, mistakes, warnings, toppings, tpk):
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
        return self._collect_shoplist(entries, mistakes, warnings, toppings)
```

- [ ] **Step 2: Write a throwaway smoke script**

Write to `<scratchpad>/smoke_pizza_visual.py` (not committed):

```python
import sys
sys.path.insert(0, "/Users/jessicaguo/Downloads/nerdygame")

from party_ui import PartyUI

ui = PartyUI()
toppings = ["pineapple", "onion"]
t_inv = [10, 2]

def phase1():
    result = ui.askEnough(3, [2, 5], t_inv, [-1, -1], toppings, True)
    print("askEnough result:", result)
    print("placements after askEnough:", ui._pizza_board.placements)
    ui.root.after(200, phase2)

def phase2():
    # same t_inv/toppings -> should reuse the SAME board, keeping placements
    result = ui.prompt(3, [2, 5], t_inv, [0, 3], [-1, -1], toppings, True)
    print("prompt result:", result)
    print("placements after prompt (should include phase1's placements):", ui._pizza_board.placements)

ui.root.after(500, phase1)
ui.root.mainloop()
```

- [ ] **Step 3: Run it and manually verify**

Run: `python3 <scratchpad>/smoke_pizza_visual.py`

Verify:
- Server sprite + counter appear dimmed and smaller as soon as the window shows.
- Inventory row (pineapple/onion pngs with counts) appears above 3 pizza bases; order list (pineapple x2, onion x5) shows on the left; checklist shows on the right.
- Click pineapple, place it on base 1 twice (inventory count next to pineapple drops from 10 to 8); check both boxes and Submit.
- In phase 2 (shopping list phase), the same pizza bases still show the 2 pineapples placed in phase 1, and the inventory count is still 8 (not reset to 10) — confirming carryover. Console output for `placements after prompt` should show base 1 still holding `["pineapple", "pineapple"]`.
- No traceback on close.

- [ ] **Step 4: Delete the smoke script and commit**

```bash
rm <scratchpad>/smoke_pizza_visual.py
cd /Users/jessicaguo/Downloads/nerdygame
git add party_ui.py
git commit -m "Wire pizza PlacementBoard into askEnough/prompt visual mode with carryover"
```

## Task 7: Cupcake plates (`quest`)

**Files:**
- Modify: `party_ui.py`

**Interfaces:**
- Consumes: `PlacementBoard` (Task 1), `self.plain_panel`/`self.visual_frame`/`self.left_panel_frame`/`self.top_inventory_frame`/`self.center_board_frame`/`self.right_panel_frame` (Task 2), `self._make_button`, `self._done`, `self._show()`.
- Produces: `PartyUI.quest(allow_cupcake_visual, num_kids, num_cakes) -> int`, `PartyUI._get_cupcake_board(num_kids, num_cakes) -> PlacementBoard` (memoized on `self._cupcake_board`).

- [ ] **Step 1: Add the cupcake methods**

Add to `party_ui.py`:

```python
    # ------------------------------------------------------------- cupcakes
    def _get_cupcake_board(self, num_kids, num_cakes):
        if self._cupcake_board is None:
            items = [("cupcake", os.path.join(self.image_dir, "cupcake.png"))]
            self._cupcake_board = PlacementBoard(
                base_image_path=os.path.join(self.image_dir, "plate.png.webp"),
                items=items, base_count=num_kids,
                initial_inventory={"cupcake": num_cakes}, show_item_switcher=False)
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
        if allow_cupcake_visual:
            return self._quest_visual(num_kids, num_cakes)
        return self._quest_plain(num_kids, num_cakes)

    def _quest_plain(self, num_kids, num_cakes):
        self._set_backdrop_dim(False)
        self.visual_frame.pack_forget()
        self.plain_panel.pack(fill="both", expand=True)

        answer_var = self._render_number_answer(self.plain_panel)

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)
        return self._collect_number_answer(answer_var)

    def _quest_visual(self, num_kids, num_cakes):
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
        return self._collect_number_answer(answer_var)
```

- [ ] **Step 2: Write a throwaway smoke script**

Write to `<scratchpad>/smoke_quest.py` (not committed):

```python
import sys
sys.path.insert(0, "/Users/jessicaguo/Downloads/nerdygame")

from party_ui import PartyUI

ui = PartyUI()

def phase1():
    result = ui.quest(False, 3, 11)
    print("plain quest result:", result)
    ui.root.after(200, phase2)

def phase2():
    result = ui.quest(True, 3, 11)
    print("visual quest result:", result)
    print("plates after phase2:", ui._cupcake_board.placements)
    ui.root.after(200, phase3)

def phase3():
    # same num_kids/num_cakes instance -> board should carry placements forward
    result = ui.quest(True, 3, 11)
    print("visual quest result 2:", result)
    print("plates after phase3 (should match end of phase2):", ui._cupcake_board.placements)

ui.root.after(500, phase1)
ui.root.mainloop()
```

- [ ] **Step 3: Run it and manually verify**

Run: `python3 <scratchpad>/smoke_quest.py`

Verify:
- Phase 1 (plain): a single centered number field + Submit appear, no board, backdrop not dimmed. Type "3", press Enter; result is `3`.
- Phase 2 (visual): backdrop dims/shrinks; a single "cupcake" inventory icon (no switcher row needed since it's the only item, but its count should still show if you kept the count label — otherwise just the plate grid) appears above 3 plates; number field appears on the left with no order list and nothing in the right panel. Click a plate twice to place 2 cupcakes on it, then type "2", Submit; result is `2`.
- Phase 3: the same plate still shows the 2 cupcakes placed in phase 2 (carryover confirmed via the printed `placements`).
- No traceback on close.

- [ ] **Step 4: Delete the smoke script and commit**

```bash
rm <scratchpad>/smoke_quest.py
cd /Users/jessicaguo/Downloads/nerdygame
git add party_ui.py
git commit -m "Implement quest() with plain and cupcake-plate visual modes"
```

## Task 8: Full end-to-end verification

**Files:**
- Modify (if issues found): `party_ui.py`, `placement_board.py`

**Interfaces:**
- Consumes: the complete `PartyUI` surface from Tasks 1-7 as called by the unmodified `bdayparty.py`.
- Produces: a confirmed-working `python3 bdayparty.py` run through all three phases.

- [ ] **Step 1: Run the real game**

Run: `python3 bdayparty.py` (from `/Users/jessicaguo/Downloads/nerdygame`)

- [ ] **Step 2: Manually verify the full flow**

Play through and confirm:
- The bubble shows the opening order text with all 6 toppings' icons and `tpk` values.
- The checklist appears (plain mode) with a row per topping showing the current `t_inv` count and a checkbox; submitting a wrong combination triggers `allow_pizza_visual` (per `bdayparty.py`'s logic) on the next round, switching to the dimmed-backdrop pizza-visual layout with correctly-locked rows carried over from the wrong submission.
- Placing/removing toppings on the pizza bases visually updates the inventory count shown in the top inventory row without changing the checklist's own numbers.
- Once `askIfEnough` finishes, `howMuchMoreNeeded`'s shopping list appears; if the pizza visual was already on, the same pizza-board placements/inventory from the end of `askIfEnough` are still shown.
- Entering wrong shopping amounts triggers `allow_pizza_visual` (if not already on) and locks in any already-correct amounts on retry.
- After both pizza phases complete, `splitCupcakes` runs: the cupcake number question appears (plain first), and once a visual is triggered, plates + a single cupcake inventory item appear with the number field on the left and no order list.
- The window never crashes or throws a traceback across the whole run, and closing it at any point exits cleanly.

- [ ] **Step 3: Fix any issues found**

If any visual glitch, crash, or logic mismatch turns up, fix it directly in `party_ui.py`/`placement_board.py` and re-run Step 1 until the full flow verifies cleanly.

- [ ] **Step 4: Commit**

```bash
cd /Users/jessicaguo/Downloads/nerdygame
git add party_ui.py placement_board.py
git commit -m "Fix issues found in end-to-end party UI verification"
```

(Skip this commit if Step 3 required no changes.)
