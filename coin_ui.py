"""Coin Trade front end for the K-5 pizza-shop math game.

A single Tkinter window (reused across rounds) with three areas: the
player's Bag (top left), the Extras pile of found coins (bottom left),
and the Bank/trade center (right). Bag and Extras each show one section
per coin type unlocked so far (copper=0, iron=1, gold=2, diamond=3, up to
mechlevel), ordered by place value with copper on the rightmost section.
Every section has 9 fixed slots laid out 5-over-4 with a digit count
above them; every coin actually present is its own clickable icon. The
Bank additionally shows 10 generic slots (any coin type, since the bank
just cares about the total of 10) and a row of one png per unlocked coin
type used only to pick which denomination the Trade button acts on.

Clicking a coin icon anywhere (Bag, Extras, or the Bank's 10 slots)
toggles it as selected; clicking anywhere else inside an area's outline
commits every currently-selected coin as a move into that area (a no-op
if nothing is selected yet). Clicking a Bank trade-type png just changes
which denomination Trade will act on. Pressing Trade fires the trade
immediately, independent of any selected coins.

Usage from cointrade.py:

    from coin_ui import CoinUI
    ui = CoinUI(image_dir="coinimages")
    info = ui.updateDisplayCoins(curr_bag, extras, curr_bank, mechlevel)
    ui.warn("message")
    ui.close()
"""

import os
import tkinter as tk

from PIL import Image, ImageTk

from shared_root import get_shared_root

COIN_NAMES = ["copper", "iron", "gold", "diamond"]

SECTION_SLOTS = 9
SECTION_COLS = 5
BANK_SLOTS = 10
BANK_COLS = 5

ICON_PX = 30
TARGET_PX = 42

BG = "#fdf6e3"
AREA_BORDER = "#3b2f1e"
SECTION_BORDER = "#d9c9a3"
TEXT = "#3b2f1e"
SLOT_EMPTY_BORDER = "#d9c9a3"
SELECTED_BORDER = "#f2a900"
SELECTED_BG = "#c543c4"
TARGET_BORDER = "#3aa655"
TARGET_BG = "#e3f5e6"
WARN_FG = "#c0392b"
BTN_BG = "#ffd27f"
BTN_ACTIVE = "#ffbe4d"


class CoinUI:
    def __init__(self, image_dir="coinimages"):
        self.image_dir = image_dir

        self.root = tk.Toplevel(get_shared_root())
        self.root.title("Coin Trade")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._done = tk.IntVar(value=0)
        self._closed = False
        self._shown = False

        self.curr_bag = [0, 0, 0, 0]
        self.extras = [0, 0, 0, 0]
        self.curr_bank = [0, [0, 0, 0, 0]]
        self.mechlevel = 0

        self.bag_selected = {t: set() for t in range(4)}
        self.extras_selected = {t: set() for t in range(4)}
        self.bank_selected = set()
        self.trade_target = 0
        self._destination = None
        self._is_trade = False

        self._load_images()
        self._build()
        self.root.withdraw()

    # ------------------------------------------------------------- images
    def _load_images(self):
        self._icons = {}
        self._target_icons = {}
        for name in COIN_NAMES:
            path = os.path.join(self.image_dir, f"{name}.png")
            pil_img = Image.open(path).convert("RGBA")

            small = pil_img.copy()
            small.thumbnail((ICON_PX, ICON_PX), Image.LANCZOS)
            self._icons[name] = ImageTk.PhotoImage(small)

            big = pil_img.copy()
            big.thumbnail((TARGET_PX, TARGET_PX), Image.LANCZOS)
            self._target_icons[name] = ImageTk.PhotoImage(big)

        blank = Image.new("RGBA", (ICON_PX, ICON_PX), (0, 0, 0, 0))
        self._blank_icon = ImageTk.PhotoImage(blank)

    # ------------------------------------------------------------- layout
    def _build(self):
        self.goal_label = tk.Label(self.root, text="", bg=BG, fg=TEXT,
                                   font=("Helvetica", 18, "bold"), height=1)
        self.goal_label.pack(pady=(14, 0))

        self.warn_label = tk.Label(self.root, text="", bg=BG, fg=WARN_FG,
                                   font=("Helvetica", 16, "bold"), height=1)
        self.warn_label.pack(pady=(4, 0))

        main = tk.Frame(self.root, bg=BG)
        main.pack(padx=20, pady=16)

        left = tk.Frame(main, bg=BG)
        left.grid(row=0, column=0, sticky="n")

        self.bag_outline, self.bag_body = self._make_area(left, "Bag")
        self.bag_outline.pack(pady=(0, 18))
        self._bind_commit_area(self.bag_outline, self.bag_body, 0)

        self.extras_outline, self.extras_body = self._make_area(left, "Extras")
        self.extras_outline.pack()
        self._bind_commit_area(self.extras_outline, self.extras_body, 1)

        right = tk.Frame(main, bg=BG)
        right.grid(row=0, column=1, sticky="n", padx=(30, 0))

        self.bank_outline, self.bank_body = self._make_area(right, "Bank")
        self.bank_outline.pack()
        self._bind_commit_area(self.bank_outline, self.bank_body, 2)

        self.bank_slots_frame = tk.Frame(self.bank_body, bg=BG)
        self.bank_slots_frame.pack(pady=(4, 12))
        self._bind_commit(self.bank_slots_frame, 2)

        self.bank_target_frame = tk.Frame(self.bank_body, bg=BG)
        self.bank_target_frame.pack(pady=(0, 10))

        self.trade_button = self._make_button(self.bank_body, "Trade",
                                              self._on_trade)
        self.trade_button.pack()

        self.bag_sections_frame = tk.Frame(self.bag_body, bg=BG)
        self.bag_sections_frame.pack()
        self._bind_commit(self.bag_sections_frame, 0)

        self.extras_sections_frame = tk.Frame(self.extras_body, bg=BG)
        self.extras_sections_frame.pack()
        self._bind_commit(self.extras_sections_frame, 1)

    def _make_area(self, parent, title):
        outline = tk.Frame(parent, bg=BG, highlightbackground=AREA_BORDER,
                           highlightthickness=3, bd=0)
        title_lbl = tk.Label(outline, text=title, bg=BG, fg=TEXT,
                             font=("Helvetica", 20, "bold"))
        title_lbl.pack(pady=(8, 4), padx=16)
        body = tk.Frame(outline, bg=BG)
        body.pack(padx=16, pady=(0, 14))
        return outline, body

    def _make_button(self, parent, text, command):
        lbl = tk.Label(parent, text=text, bg=BTN_BG, fg=TEXT,
                       font=("Helvetica", 18, "bold"), padx=18, pady=6,
                       bd=4, relief="raised", cursor="hand2")
        lbl.bind("<Button-1>", lambda e: command())
        lbl.bind("<Enter>", lambda e: lbl.configure(bg=BTN_ACTIVE))
        lbl.bind("<Leave>", lambda e: lbl.configure(bg=BTN_BG))
        return lbl

    def _bind_commit_area(self, outline, body, destination):
        self._bind_commit(outline, destination)
        for w in outline.winfo_children():
            if w is not body:
                self._bind_commit(w, destination)

    def _bind_commit(self, widget, destination):
        widget.bind("<Button-1>", lambda e: self._try_commit(destination))

    # ---------------------------------------------------------------- API
    def updateDisplayCoins(self, curr_bag, extras, curr_bank, mechlevel):
        if self._closed:
            return ([], self.trade_target, 0, False)

        self.curr_bag = curr_bag
        self.extras = extras
        self.curr_bank = curr_bank
        self.mechlevel = mechlevel

        self.bag_selected = {t: set() for t in range(4)}
        self.extras_selected = {t: set() for t in range(4)}
        self.bank_selected = set()
        self._destination = None
        self._is_trade = False
        self._done.set(0)

        self._render_all()

        if not self._shown:
            self.root.deiconify()
            self._center_window()
            self._shown = True

        self.root.wait_variable(self._done)

        if self._closed:
            return ([], self.trade_target, 0, False)

        return (self._selected_coins(), self.trade_target,
                self._destination if self._destination is not None else 2,
                self._is_trade)

    def showGoal(self, amount, mechlevel):
        if self._closed:
            return
        parts = [f"{amount[t]} {COIN_NAMES[t]}" for t in range(mechlevel, -1, -1)]
        text = "Return (" + ", ".join(parts) + ")" if parts else "Return (0)"
        self.goal_label.configure(text=text)

    def bankToBag(self, curr_bag, bank_counts):
        if self._closed:
            return
        self.curr_bag = curr_bag
        self.curr_bank = [self.curr_bank[0], bank_counts]
        self.bank_selected = set()
        self._render_all()
        self.root.update_idletasks()

    def warn(self, message):
        if self._closed:
            return
        self.warn_label.configure(text=message)

    def close(self, delay_ms=0):
        if not self._closed:
            if delay_ms:
                self._pause(delay_ms)
            self._closed = True
            try:
                self.root.destroy()
            except tk.TclError:
                pass

    # ------------------------------------------------------------ render
    def _render_all(self):
        self._render_section(self.bag_sections_frame, self.curr_bag,
                             self.bag_selected, 0)
        self._render_section(self.extras_sections_frame, self.extras,
                             self.extras_selected, 1)
        self._render_bank()

    def _render_section(self, parent, counts, selected_map, loc):
        for w in parent.winfo_children():
            w.destroy()

        for t in range(self.mechlevel, -1, -1):
            section = tk.Frame(parent, bg=BG, highlightbackground=SECTION_BORDER,
                               highlightthickness=2)
            section.pack(side="left", padx=6)
            self._bind_commit(section, loc)

            count = max(0, min(SECTION_SLOTS, counts[t]))
            digit = tk.Label(section, text=str(counts[t]), bg=BG, fg=TEXT,
                             font=("Helvetica", 16, "bold"))
            digit.pack(pady=(4, 2))
            self._bind_commit(digit, loc)

            grid = tk.Frame(section, bg=BG)
            grid.pack(padx=4, pady=(0, 6))
            self._bind_commit(grid, loc)

            for i in range(SECTION_SLOTS):
                r, c = divmod(i, SECTION_COLS)
                if i < count:
                    selected = i in selected_map[t]
                    slot = tk.Label(grid, image=self._icons[COIN_NAMES[t]],
                                    bg=SELECTED_BG if selected else BG,
                                    highlightbackground=SELECTED_BORDER if selected else BG,
                                    highlightthickness=2, cursor="hand2")
                    slot.grid(row=r, column=c, padx=2, pady=2)
                    slot.bind("<Button-1>",
                             lambda e, tt=t, ii=i: self._toggle_slot(loc, tt, ii))
                else:
                    slot = tk.Label(grid, image=self._blank_icon, bg=BG,
                                    highlightbackground=SLOT_EMPTY_BORDER,
                                    highlightthickness=1)
                    slot.grid(row=r, column=c, padx=2, pady=2)
                    self._bind_commit(slot, loc)

    def _bank_slot_types(self):
        counts = self.curr_bank[1]
        slot_types = []
        for t in range(4):
            slot_types += [t] * counts[t]
        return slot_types[:BANK_SLOTS]

    def _render_bank(self):
        for w in self.bank_slots_frame.winfo_children():
            w.destroy()

        slot_types = self._bank_slot_types()
        for i in range(BANK_SLOTS):
            r, c = divmod(i, BANK_COLS)
            if i < len(slot_types):
                t = slot_types[i]
                selected = i in self.bank_selected
                slot = tk.Label(self.bank_slots_frame, image=self._icons[COIN_NAMES[t]],
                                bg=SELECTED_BG if selected else BG,
                                highlightbackground=SELECTED_BORDER if selected else BG,
                                highlightthickness=2, cursor="hand2")
                slot.grid(row=r, column=c, padx=2, pady=2)
                slot.bind("<Button-1>", lambda e, ii=i: self._toggle_bank_slot(ii))
            else:
                slot = tk.Label(self.bank_slots_frame, image=self._blank_icon, bg=BG,
                                highlightbackground=SLOT_EMPTY_BORDER,
                                highlightthickness=1)
                slot.grid(row=r, column=c, padx=2, pady=2)
                self._bind_commit(slot, 2)

        for w in self.bank_target_frame.winfo_children():
            w.destroy()
        for t in range(self.mechlevel, -1, -1):
            is_target = t == self.trade_target
            icon = tk.Label(self.bank_target_frame, image=self._target_icons[COIN_NAMES[t]],
                            bg=TARGET_BG if is_target else BG,
                            highlightbackground=TARGET_BORDER if is_target else BG,
                            highlightthickness=3, cursor="hand2")
            icon.pack(side="left", padx=6)
            icon.bind("<Button-1>", lambda e, tt=t: self._set_trade_target(tt))

    # ------------------------------------------------------------- input
    def _toggle_slot(self, loc, t, i):
        m = self.bag_selected if loc == 0 else self.extras_selected
        m[t].symmetric_difference_update({i})
        self._render_all()

    def _toggle_bank_slot(self, i):
        self.bank_selected.symmetric_difference_update({i})
        self._render_all()

    def _set_trade_target(self, t):
        self.trade_target = t
        self._render_bank()

    def _any_selected(self):
        return (any(self.bag_selected[t] for t in self.bag_selected)
                or any(self.extras_selected[t] for t in self.extras_selected)
                or bool(self.bank_selected))

    def _try_commit(self, destination):
        if not self._any_selected():
            return
        self._destination = destination
        self._is_trade = False
        self._done.set(1)

    def _on_trade(self):
        self._is_trade = True
        self._destination = 2
        self._done.set(1)

    def _selected_coins(self):
        result = []
        for t in range(4):
            bag_ct = len(self.bag_selected[t])
            extras_ct = len(self.extras_selected[t])
            bank_ct = sum(1 for i in self.bank_selected
                         if i < len(self._bank_slot_types()) and self._bank_slot_types()[i] == t)
            if bag_ct or extras_ct or bank_ct:
                result.append([t, [bag_ct, extras_ct, bank_ct]])
        return result

    # ------------------------------------------------------------ window
    def _center_window(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")

    def _pause(self, ms):
        if self._closed:
            return
        hold = tk.IntVar(value=0)
        self.root.after(ms, lambda: hold.set(1))
        self.root.wait_variable(hold)

    def _on_close(self):
        self._closed = True
        self._done.set(1)
        try:
            self.root.destroy()
        except tk.TclError:
            pass
