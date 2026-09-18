"""Grocery-shop front end for the K-5 pizza-shop math game.

A single Tkinter window (reused across rounds) that shows a prompt -- a numeral
next to one picture of a grocery item -- and ONE card at a time, numbered 1..20.
The card shows that many pictures of the item laid out in a 5-wide "ten-frame"
grid so kindergarteners get a sense of how the numbers compare; the card's own
numeral is only revealed once the player is struggling (mistake level 2-3).  The
player steps between cards with the big minus / plus buttons and clicks the card
to choose it.  A new round keeps whatever card the player left off on.

Usage from grocshop.py:

    from grocery_ui import GroceryShopUI

    ui = GroceryShopUI(image_dir="images")
    value = ui.ask(prompt, item)          # -> int the player locked in (or None)
    ...
    ui.close()

Only dependency beyond the standard library is Pillow (PIL), which is used
because the bundled Tk 8.5 cannot load PNGs on its own.
"""

import os
import tkinter as tk
from tkinter import font as tkfont

from PIL import Image, ImageDraw, ImageTk

from shared_root import get_shared_root

CARD_COUNT = 20
ICON_COLS = 5          # icons per row on a card -> stacked ten-frames
ICON_PX = 26           # icon size on a card
CARD_W = 210
CARD_H = 250

BOUGHT_ICON_PX = 30
BOUGHT_BG = "#ffffff"
BOUGHT_BORDER = "#d9c9a3"
MISTAKE_RED = "#c0392b"  # matches coin_ui.py's WARN_FG / slice_ui.py's EMPHASIS_COLOR

# Warm, high-contrast palette for young players.
BG = "#fdf6e3"
CARD_BG = "#ffffff"
CARD_BORDER = "#d9c9a3"
FOCUS_BG = "#fff3c4"
FOCUS_BORDER = "#f2a900"
TARGET_BORDER = "#3aa655"
TEXT = "#3b2f1e"
ACCENT = "#e8541e"
BTN_BG = "#ffd27f"
BTN_ACTIVE = "#ffbe4d"


class GroceryShopUI:
    def __init__(self, image_dir="images"):
        self.image_dir = image_dir

        self.root = tk.Toplevel(get_shared_root())
        self.root.title("Grocery Store")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._done = tk.IntVar(value=0)   # bumped to release ask()
        self._answer = None
        self._closed = False
        self._imgs = []                   # keep PhotoImage refs alive
        self._tk_icon = None              # this round's item icon

        self._bought = []                 # [(item, amount), ...] this session
        self._bought_icons = {}           # item name -> small PhotoImage, kept
                                          # alive independently of self._imgs
        self._bought_icons_struck = {}    # item name -> icon with a red
                                          # strikethrough, for superseded
                                          # (mistaken) prior entries

        self.focus_idx = 1                # persists across rounds
        self.target = None
        self.current_item = None
        self.indicate_direction = False
        self.indicate_number = False
        self.first_click = True

        self.num_font = tkfont.Font(family="Helvetica", size=40, weight="bold")
        self.prompt_font = tkfont.Font(family="Helvetica", size=72, weight="bold")
        self.bought_font = tkfont.Font(family="Helvetica", size=13, weight="bold")
        self.bought_struck_font = tkfont.Font(family="Helvetica", size=13,
                                              weight="bold", overstrike=True)

        self._build()
        self.root.withdraw()

    # ------------------------------------------------------------------ build
    def _build(self):
        # --- prompt: numeral + one picture, nothing else --------------------
        top = tk.Frame(self.root, bg=BG)
        top.pack(pady=(22, 6), padx=24)


        self.prompt_num = tk.Label(top, text="", bg=BG, fg=ACCENT,
                                   font=self.prompt_font, width=2)
        self.prompt_num.pack(side="left")
        self.prompt_img = tk.Label(top, bg=BG)
        self.prompt_img.pack(side="left", padx=18)

        # --- one card at a time, between the [ - ] and [ + ] buttons,
        # plus the "Bought So Far" list, side by side ------------------------
        content_row = tk.Frame(self.root, bg=BG)
        content_row.pack(pady=8, padx=16)

        mid = tk.Frame(content_row, bg=BG)
        mid.pack(side="left")

        self._minus = self._make_button(mid, "−", lambda: self._bump(-1))
        self._minus.pack(side="left", padx=(0, 16))

        # card_column stacks the hint directly above the card, so the hint
        # stays centered over the card itself even though the window is
        # wider than the card (the minus/plus buttons and the "Bought So
        # Far" panel sit outside this column).
        card_column = tk.Frame(mid, bg=BG)
        card_column.pack(side="left")

        self.hint = tk.Label(card_column, text="", bg=BG, fg=TARGET_BORDER,
                             font=("Helvetica", 18, "bold"), height=1)
        self.hint.pack()

        self.card = tk.Frame(card_column, bg=CARD_BG, width=CARD_W, height=CARD_H,
                             highlightbackground=FOCUS_BORDER,
                             highlightcolor=FOCUS_BORDER, highlightthickness=5,
                             cursor="hand2")
        self.card.pack(side="left")
        self.card.pack_propagate(False)

        # card_num only takes up vertical space while it's actually shown
        # (indicate_number, high mistake levels) -- otherwise an empty-text
        # Label at this font size would still reserve its full line height
        # and push card_icons off-center within the card at high counts.
        self.card_num = tk.Label(self.card, text="", bg=CARD_BG, fg=TEXT,
                                 font=self.num_font)
        self.card_icons = tk.Frame(self.card, bg=CARD_BG)
        self.card_icons.pack(expand=True)

        for w in (self.card, self.card_num, self.card_icons):
            w.bind("<Button-1>", lambda e: self._lock(self.focus_idx))

        self._plus = self._make_button(mid, "+", lambda: self._bump(1))
        self._plus.pack(side="left", padx=(16, 0))

        bought_box = tk.Frame(content_row, bg=BOUGHT_BG,
                              highlightbackground=BOUGHT_BORDER, highlightthickness=2)
        bought_box.pack(side="left", padx=(24, 0), fill="y")
        tk.Label(bought_box, text="Bought So Far", bg=BOUGHT_BG, fg=TEXT,
                font=("Helvetica", 15, "bold")).pack(pady=(10, 6), padx=16)
        self.bought_list = tk.Frame(bought_box, bg=BOUGHT_BG)
        self.bought_list.pack(padx=16, pady=(0, 14))

        self.root.bind("<Left>", lambda e: self._bump(-1))
        self.root.bind("<Right>", lambda e: self._bump(1))
        self.root.bind("<minus>", lambda e: self._bump(-1))
        self.root.bind("<plus>", lambda e: self._bump(1))
        self.root.bind("<equal>", lambda e: self._bump(1))
        self.root.bind("<Return>", lambda e: self._lock(self.focus_idx))

    def _make_button(self, parent, text, command, bg=BTN_BG, fg=TEXT,
                     font=("Helvetica", 34, "bold"), padx=16, pady=6):
        # Labels instead of tk.Button: macOS Tk 8.5 ignores Button colors.
        lbl = tk.Label(parent, text=text, bg=bg, fg=fg, font=font,
                       padx=padx, pady=pady, bd=4, relief="raised", cursor="hand2")
        lbl.bind("<Button-1>", lambda e: command())
        lbl.bind("<Enter>", lambda e: lbl.configure(bg=BTN_ACTIVE)
                 if bg == BTN_BG else None)
        lbl.bind("<Leave>", lambda e: lbl.configure(bg=bg))
        return lbl

    # ---------------------------------------------------------------- rounds
    def ask(self, prompt, item, indicate_direction=False, indicate_number=False):
        """Show one round and block until the player locks a card in.

        Returns the chosen number as an int, or None if the player closed
        the window.
        """
        if self._closed:
            return None

        prompt = int(prompt)
        self.target = prompt
        self.current_item = item
        self.indicate_direction = bool(indicate_direction)
        self.indicate_number = bool(indicate_number)
        self.first_click = True

        pil_item = self._load_item(item)
        self._imgs = []  # drop last round's images

        big = pil_item.copy()
        big.thumbnail((150, 150), Image.LANCZOS)
        tk_big = ImageTk.PhotoImage(big)
        self._imgs.append(tk_big)
        self.prompt_img.configure(image=tk_big)
        self.prompt_num.configure(text=str(prompt))

        self._prep_icon(pil_item)
        # focus_idx is deliberately left where the previous round ended
        self.hint.configure(text="")
        self._answer = None
        self._done.set(0)

        self.root.deiconify()
        self.root.update_idletasks()
        self._center_window()
        self._render_card()
        self._render_bought()

        self.root.wait_variable(self._done)
        self.root.withdraw()
        return self._answer

    def close(self):
        if not self._closed:
            self._closed = True
            try:
                self.root.destroy()
            except tk.TclError:
                pass

    # ------------------------------------------------------------- internals
    def _load_item(self, item):
        path = os.path.join(self.image_dir, f"{item}.png")
        return Image.open(path).convert("RGBA")

    def _prep_icon(self, pil_item):
        thumb = pil_item.copy()
        thumb.thumbnail((ICON_PX, ICON_PX), Image.LANCZOS)
        self._tk_icon = ImageTk.PhotoImage(thumb)
        self._imgs.append(self._tk_icon)

    def _bump(self, delta):
        self.focus_idx = min(CARD_COUNT, max(1, self.focus_idx + delta))
        self.first_click = False
        self._render_card()

    def _render_card(self):
        n = self.focus_idx

        # The card's own numeral is only shown when the game asks for it
        # (mistake level 2-3 -> indicate_number); otherwise the player has
        # to count the pictures. Unpacked (not just blanked) when hidden,
        # so it reserves no space and card_icons stays centered on the
        # card even at high counts -- see the comment at its creation.
        if self.indicate_number:
            self.card_num.configure(text=str(n))
            if not self.card_num.winfo_ismapped():
                self.card_num.pack(pady=(8, 2), before=self.card_icons)
        else:
            self.card_num.configure(text="")
            self.card_num.pack_forget()

        for child in self.card_icons.winfo_children():
            child.destroy()
        for i in range(n):
            r, c = divmod(i, ICON_COLS)
            lbl = tk.Label(self.card_icons, image=self._tk_icon, bg=CARD_BG)
            lbl.grid(row=r, column=c, padx=1, pady=1)
            lbl.bind("<Button-1>", lambda e: self._lock(self.focus_idx))

        at_target = self.indicate_number and n == self.target
        border = TARGET_BORDER if at_target else FOCUS_BORDER
        self.card.configure(highlightbackground=border, highlightcolor=border)
        self._update_hint()

    def _update_hint(self):
        if not self.indicate_direction or self.target is None or not self.first_click:
            self.hint.configure(text="")
            return
        if self.focus_idx < self.target:
            self.hint.configure(text="-->")
        elif self.focus_idx > self.target:
            self.hint.configure(text="<--")

    def _center_window(self):
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")

    def _lock(self, value):
        self._answer = int(value)
        self._bought.append((self.current_item, self._answer))
        self._done.set(1)

    def _bought_icon(self, item):
        if item not in self._bought_icons:
            thumb = self._load_item(item)
            thumb.thumbnail((BOUGHT_ICON_PX, BOUGHT_ICON_PX), Image.LANCZOS)
            self._bought_icons[item] = ImageTk.PhotoImage(thumb)
        return self._bought_icons[item]

    def _bought_icon_struck(self, item):
        if item not in self._bought_icons_struck:
            thumb = self._load_item(item)
            thumb.thumbnail((BOUGHT_ICON_PX, BOUGHT_ICON_PX), Image.LANCZOS)
            ImageDraw.Draw(thumb).line(
                [(0, 0), (thumb.width, thumb.height)], fill=MISTAKE_RED, width=3)
            self._bought_icons_struck[item] = ImageTk.PhotoImage(thumb)
        return self._bought_icons_struck[item]

    def _render_bought(self):
        for w in self.bought_list.winfo_children():
            w.destroy()
        # A mistake means the same item gets locked in more than once this
        # session; only the LAST entry for a given item is the one that
        # actually completed the round (grocshop.py keeps re-asking for
        # the same item until it's answered correctly), so every earlier
        # entry for that item is a superseded mistake -- cross it out.
        last_index = {}
        for i, (item, _amount) in enumerate(self._bought):
            last_index[item] = i
        for i, (item, amount) in enumerate(self._bought):
            superseded = i != last_index[item]
            row = tk.Frame(self.bought_list, bg=BOUGHT_BG)
            row.pack(anchor="w", pady=2)
            icon = self._bought_icon_struck(item) if superseded else self._bought_icon(item)
            tk.Label(row, image=icon, bg=BOUGHT_BG).pack(side="left")
            font = self.bought_struck_font if superseded else self.bought_font
            fg = MISTAKE_RED if superseded else TEXT
            tk.Label(row, text=f"x{amount}", bg=BOUGHT_BG, fg=fg,
                    font=font).pack(side="left", padx=(6, 0))

    def _on_close(self):
        self._answer = None
        self._closed = True
        self._done.set(1)
