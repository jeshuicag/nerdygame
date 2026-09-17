# Slice UI Design

Date: 2026-09-17

## Purpose

`bySlice.py` (backend/logic, already fixed and working) drives a
fraction-of-a-pizza game: a customer (or two, at once) asks for `numer/denom`
pizza; the player must cut a pizza into exactly `denom` equal slices
(`cutPizza`/`makeCuts`), then hand over exactly `numer` of those slices onto
a plate (`handOver`/`onPlate`). `slice_ui.py` is currently an empty stub
(`class SliceUI: pass`). This spec defines its Tkinter+PIL implementation,
following the same conventions established in `party_ui.py`/
`coin_ui.py`/`grocery_ui.py`: a single persistent window, `wait_variable`
blocking calls, a warm color palette, off-white titled boxes.

## Backend interface (unchanged, already implemented in bySlice.py)

```
SliceUI(image_dir="sliceimages")

.speak(text)                          -> None   # left customer's bubble
.speak2(text)                         -> None   # right customer's bubble
.makeCuts(denom2)                     -> (slice1, slice2)
.onPlate(denom, denom2)               -> (slices1, slices2)
```

`denom2`/`numer2` are `None` when there's only one customer (`double=False`
in `serveCustomers`). `slice2`/`slices2` must be `None` whenever `denom2`
is `None` — the UI must not invent a value for a customer that doesn't
exist.

## Assets

- `sliceimages/1slice.PNG`, `2slice-1/2.PNG`, `3slice-1/2/3.PNG`,
  `4slice-1..4.PNG`, `5slice-1..5.PNG` — note the uppercase `.PNG`
  extension (unlike the rest of the project's lowercase `.png`); paths
  must match exactly. All share the same 4320x4320 canvas, so overlaying
  every `Nslice-*` image for a given N reconstructs a full pizza cut into
  N wedges with transparent backgrounds elsewhere.
- `sliceimages/customer1.png` (left customer), `sliceimages/customer2.png`
  (right customer).
- Reused from the party game: `partyimages/counter.png` (the counter) and
  `partyimages/plate.png.webp` (the surface slices land on during
  handover).

## Window layout

One persistent window, matching `party_ui.py`'s pattern: create once in
`__init__`, `deiconify`/show on first use, reuse across every call.

```
+--------------------------------------------------+
|  customer1 zone          |      customer2 zone    |
|  [speech bubble]         |      [speech bubble]    |
|  [customer1.png] [pizza] |  [pizza] [customer2.png]|
|  (mirrored: customer     |  (mirrored: pizza on    |
|   art on the outside,    |   the outside, customer |
|   pizza toward center)   |   art toward center)    |
+--------------------------------------------------+
|              counter.png (spans full width)        |
+--------------------------------------------------+
```

Left/right zones are always present in the layout. When there's no second
customer (`denom2 is None` for the whole round), the right zone's content
is simply never populated for that round — it renders empty.

## `speak`/`speak2`

Same non-blocking bubble-update pattern as `party_ui.py`'s `server`/
`display`: update the corresponding customer's speech bubble text and
return immediately, no interaction.

## `makeCuts(denom2)` — cutPizza phase

For each active customer (always customer1; customer2 only if `denom2 is
not None`):

- The pizza starts at 1 slice (`1slice.PNG`) each time `makeCuts` is
  called (no carry-over between retries or rounds — matches the
  project's default; shopping-list-style persistence was a specific,
  separately-requested exception elsewhere, not a general rule).
- Clicking anywhere on the pizza cycles its slice count: 1 -> 2 -> 3 -> 4
  -> 5 -> back to 1. At slice count N, all N `Nslice-*.PNG` images are
  drawn overlaid (stacked `Label`s or one composited image) to form the
  cut pizza.
- Each pizza has its own "New Pizza" button beneath it that resets just
  that pizza back to 1 slice.
- One shared "Cut" button (not per-pizza) locks in both pizzas' current
  slice counts and unblocks the call.

Returns `(slice1, slice2)`, where `slice2` is `None` when there's no
second customer.

## `onPlate(denom, denom2)` — handOver phase

For each active customer, a fresh **fully-cut** pizza is shown — `denom`
(or `denom2`) individually-clickable slice pieces, matching how `cutPizza`
confirmed it (the loop that calls `makeCuts` only exits once the returned
count equals the target, so by the time `handOver` runs the "correct"
piece count is exactly `denom`/`denom2`). A plate area sits alongside it.

- Clicking a slice piece still on the pizza moves it onto the plate.
- Clicking a piece already on the plate moves it back onto the pizza.
- An "Add Pizza" button per customer adds another *whole* pizza (same
  `denom`/`denom2` piece count, all pieces starting on the pizza, none on
  the plate) alongside any pizza(s) that customer already has — for
  improper fractions (`numer > denom`), where more than one pizza's worth
  of slices is needed. A customer can end up with several pizzas at once;
  all of their pieces (from any of their pizzas) can be clicked onto the
  same shared plate for that customer.
- One shared "Hand Over" button (not per-customer) locks in both
  customers' current plate counts and unblocks the call.

Returns `(slices1, slices2)` — the total slice count on each customer's
plate (summed across all of that customer's pizzas), `slices2` `None` when
there's no second customer.

## Non-goals

- No changes to `bySlice.py`'s game logic — it's already correct
  (confirmed: parses cleanly, `rounds`/`round` and the `handOver` loop
  condition bugs found during review are fixed).
- No automated test suite — matches every other `*_ui.py` in this project;
  verification is manual (headless-driven smoke scripts during
  development, then a real playthrough).
- No cross-round state persistence (each `makeCuts`/`onPlate` call starts
  fresh) unless the user asks for it later, the same way shopping-list
  persistence was requested as a specific follow-up for `party_ui.py`
  rather than assumed upfront.
