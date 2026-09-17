# Party UI Design

Date: 2026-09-16

## Purpose

`bdayparty.py` (backend/logic) drives a three-phase party game — checking
pizza-topping inventory (`askIfEnough`), restocking short toppings
(`howMuchMoreNeeded`), and splitting cupcakes (`splitCupcakes`) — but
`party_ui.py` is currently an empty class stub. This spec defines the
Tkinter+PIL frontend that implements the `PartyUI` interface `bdayparty.py`
already calls, following the single-persistent-window, blocking-call
conventions established in `coin_ui.py` and `grocery_ui.py`.

## Backend interface (unchanged, defines the contract)

```
PartyUI(image_dir="partyimages", toppings_dir="shopimages")

.server(text, tpk, toppings)                                  -> None
.display(text, a, b)                                          -> None   # a, b always None today
.askEnough(num_kids, tpk, t_inv, mistakes, toppings,
           allow_pizza_visual)                                -> list[int]  # 0/1 per topping
.prompt(kids, tpk, t_inv, mistakes, warnings, toppings,
        allow_pizza_visual)                                   -> list[int]  # amount to buy per topping
.quest(allow_cupcake_visual, num_kids, num_cakes)              -> int
```

`toppings`/`tpk`/`t_inv`/`mistakes`/`warnings` are parallel lists indexed by
topping. `mistakes[i]` in {0,2} means topping `i` is already answered
correctly (even), {1,3} means it's still wrong (odd), `-1` means unanswered.
`warnings[i] == 0` means the buy amount for topping `i` is already correct.

## Shared component: `PlacementBoard`

All three phases reduce to the same shape: a speech bubble, an answer
widget, and an optional full-screen visual builder with clickable bases and
an inventory the player places onto/removes from them. Rather than three
bespoke widgets, `party_ui.py` implements one `PlacementBoard` class used
for both the pizza board and the cupcake/plate board, parameterized by:

- `items`: list of (name, image) pairs — 6 toppings, or a single `("cupcake", ...)`
- `base_image`, `base_count`: pizza base × `num_kids`, or plate × `num_kids`
- `show_item_switcher`: `True` for toppings (multiple items to choose an
  active one from), `False` for cupcakes (only one item, always active)

State per board (placements per base, and a working inventory copy) lives
on the board instance, not recreated each call — see "Cross-phase
carryover" below.

## Window layout — normal mode (`allow_*_visual` False)

```
+--------------------------------------+
|         Server speech bubble         |  <- text; if tpk/toppings given
|                                       |     (not None), one row per
|                                       |     topping: icon + tpk number
+--------------------------------------+
|   Checklist / Shopping list / blank  |  <- middle zone (blank while
|                                       |     splitCupcakes hasn't yet
|                                       |     turned the visual on)
+--------------------------------------+
|  Counter (spans full width)          |
|  [Server sprite, left, behind        |
|   counter]                           |
+--------------------------------------+
```

One persistent `tk.Tk()` window is created in `PartyUI.__init__`, reused
across every call, matching `coin_ui.py`/`grocery_ui.py`.

## Window layout — visual mode (`allow_pizza_visual` / `allow_cupcake_visual` True)

The bubble stays exactly where it is. Server sprite + counter render at
reduced opacity as a backdrop, and the middle zone expands to fill the
rest of the window (covering the space the counter/server would otherwise
occupy) with the `PlacementBoard` plus the still-visible answer widget:

```
+--------------------------------------------------+
|         Server speech bubble (unchanged)          |
+--------------------------------------------------+
| [dimmed server sprite + counter as backdrop]      |
|  Inventory row: clickable item pngs, active one   |
|  emphasized (bordered/enlarged, like coin_ui's    |
|  bank trade-target icons)                         |
|                                                    |
|  Pizza:  [Order list |  Base grid  | Checklist /  |
|           right]     |  (click to  |  Shopping    |
|                       |   place/    |  list, right |
|                       |   remove)   |              |
|                                                    |
|  Cupcakes: [Number-answer field, left] | [Plate    |
|             (no order list — nothing               |
|              to reference)          grid]          |
+--------------------------------------------------+
```

Pizza: order list (topping icon + `tpk` number, static reference) and the
checklist/shopping list both sit on the right. Cupcakes: no order list;
the single number-answer field sits on the **left** instead.

Placing/removing items on a base only mutates the board's own working
inventory copy (initialized from `t_inv`/`num_cakes` the first time the
board is shown) — it is a visualization aid only and never feeds answers
back to the backend directly. The player still enters the checklist
checkbox / shopping-list amount / cupcake number themselves.

## Checklist (`askEnough`)

One row per topping: icon, numeral showing `t_inv[i]`, and a checkbox
(checked = "enough", unchecked = "not enough"). A Submit button reads all
checkboxes into the `enough` list.

Retry behavior: rows where `mistakes[i] % 2 == 0` (already correct) render
dimmed/disabled, showing their last submitted checked state, and are
excluded from editing; only rows still odd (or unanswered, `-1`) are
interactive. `PartyUI` keeps a `self._checklist_state: dict[int, bool]` to
remember prior submissions per topping index for redisplay.

## Shopping list (`prompt`)

Rows only for toppings needing restock (`mistakes[i] in {2, 3}`), each
with a text-entry field for the amount to buy. A Submit button reads the
fields into the `added` list (0 for toppings not shown, i.e. `mistakes[i]
in {0, 1}`).

Retry behavior: rows where `warnings[i] == 0` (already correct amount)
render locked/dimmed showing the previously entered amount as static
text; other shown rows stay editable. `PartyUI` keeps a
`self._shoplist_state: dict[int, int]` for redisplay.

## Cross-phase carryover

`PartyUI` keeps the pizza `PlacementBoard` instance (with its placements
and working inventory) alive for the lifetime of the game object. It is
initialized from `t_inv` the first time `allow_pizza_visual` is `True`
(in `askEnough` or `prompt`, whichever hits first) and is never reset
automatically afterward, so the same placements/working inventory that
existed at the end of `askIfEnough` are still there when
`howMuchMoreNeeded` shows the board again. The cupcake `PlacementBoard`
(plates) is entirely separate state, following the same
initialize-once-on-first-use rule, independent of the pizza board.

## `display` / `quest` (cupcakes)

`display(text, None, None)` reuses the speech-bubble component with no
topping breakdown row (bubble-only update, non-blocking).

`quest(allow_cupcake_visual, num_kids, num_cakes)` shows a single
text-entry number field (Enter or a Submit button locks in the answer)
plus, when `allow_cupcake_visual` is `True`, the plate `PlacementBoard`
(one plate per kid, single "cupcake" inventory item, no item-switcher
needed since there's only one item, no order list). Returns the entered
int.

## Non-goals

- No changes to `bdayparty.py`'s game logic, randomization, or the
  `PartyUI` method signatures it already calls.
- No automated test suite — consistent with `coin_ui.py`/`grocery_ui.py`,
  verification is manual: run `bdayparty.py` through all three phases,
  including forcing mistakes to exercise `allow_pizza_visual` /
  `allow_cupcake_visual` and the retry-locking behavior.
- No persistence across separate game runs (process restarts) — board
  state lives only in the `PartyUI` instance for one `playParty` call.
