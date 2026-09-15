"""Party front end for the K-5 pizza-shop math game.

A single Tkinter window (reused across rounds) with a server speech bubble
at the top and a content area below that is rebuilt for each of the three
calls bdayparty.py makes:

  * askEnough(num_kids, tpk, t_inv, mistakes, toppings, allow_pizza_visual)
    -- the server announces how many kids there are and how much of each
    topping each kid wants; below that, a checklist shows one row per
    topping (icon + current fridge count) with three chip buttons --
    Just Right / Too Much / Too Little -- exactly one selectable per row.
    A row whose last-round guess was wrong (an odd value in `mistakes`) is
    outlined in red. Submit is disabled until every row has a pick, and
    returns the array `askIfEnough` expects (0=too much,1=too little,
    2=right amount).

  * prompt(kids, tpk, t_inv, mistakes, warnings, toppings,
    allow_pizza_visual, added) -- only toppings whose `mistakes` says
    "too much" or "too little" get a control at all; toppings already
    right are just shown, untouchable. The player focuses one adjustable
    topping at a time (clicking its icon); focusing a topping always
    starts it fresh -- empty pizza bases and a visual "available" count
    reset from the fridge total, regardless of what was placed the last
    time it was focused. Once `allow_pizza_visual` and the topping needs
    MORE (not less), one pizza per kid is shown; clicking a pizza adds one
    unit of the focused topping to it (subtracting from the visual
    available count), and a bulk button adds one to every pizza at once
    when there's enough left to do that. A plain +/- total is always
    available too (so the puzzle is never stuck even if the fridge count
    runs out before the real answer is reached), and toppings needing
    LESS always use that plain +/- (there's no "remove from a pizza"
    visual). Submit returns the running total for every topping.

  * quest(text, num_kids, num_cakes, allow_cupcake_visual, plated, pkid,
    rem) -- `text` is always shown verbatim as the server's own words.
    When `allow_cupcake_visual` is True and `plated` is False, one empty
    plate per kid is shown and the player can click plates (or a bulk
    "add 1 to every plate" button) to manually distribute the cupcake
    pile, as a manipulative -- it never computes the answer for them.
    When `plated` is True, the plates are shown already holding `pkid`
    cupcakes each plus a separate leftover pile of `rem`, purely so the
    player can count it. Either way the actual answer is always typed
    into a number field and submitted.

Usage from bdayparty.py:

    from party_ui import PartyUI
    ui = PartyUI(image_dir="partyimages", toppings_dir="shopimages")
    enough = ui.askEnough(num_kids, tpk, t_inv, mistakes, toppings, allow_pizza_visual)
    ui.display("message")
    added = ui.prompt(kids, tpk, t_inv, mistakes, warnings, toppings, allow_pizza_visual, added)
    answer = ui.quest(text, num_kids, num_cakes, allow_cupcake_visual, plated, pkid, rem)
    ui.close()
"""

import os
import tkinter as tk

from PIL import Image, ImageTk

BG = "#fdf6e3"
TEXT = "#3b2f1e"
ACCENT = "#e8541e"
CARD_BG = "#ffffff"
CARD_BORDER = "#d9c9a3"
WRONG_BORDER = "#c0392b"
FOCUS_BORDER = "#2f6fed"
SELECTED_BG = "#fff3c4"
SELECTED_BORDER = "#f2a900"
BTN_BG = "#ffd27f"
BTN_ACTIVE = "#ffbe4d"
DISABLED_BG = "#e8ddc0"
DISABLED_FG = "#b8ab8a"

TOPPING_PX = 40
SERVER_PX = 150
COUNTER_H_PX = 65
BASE_PX = 60
PILE_PX = 22
GRID_COLS = 5
SPEECH_WRAP = 620


class PartyUI:
    def __init__(self, image_dir="partyimages", toppings_dir="shopimages"):
        self.image_dir = image_dir
        self.toppings_dir = toppings_dir

        self.root = tk.Tk()
        self.root.title("Party Time")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._done = tk.IntVar(value=0)
        self._closed = False
        self._shown = False

        self._topping_icons = {}
        self._static_icons = {}
        self._load_static_images()

        self._enough_selected = {}
        self._focused_topping = None

        self._build()
        self.root.withdraw()

    # ------------------------------------------------------------- images
    def _open_image(self, base_dir, name):
        for suffix in (".png", ".png.webp", ".webp"):
            path = os.path.join(base_dir, name + suffix)
            if os.path.exists(path):
                return Image.open(path).convert("RGBA")
        raise FileNotFoundError(f"no image found for '{name}' in {base_dir}")

    def _to_icon(self, pil_img, px):
        thumb = pil_img.copy()
        thumb.thumbnail((px, px), Image.LANCZOS)
        return ImageTk.PhotoImage(thumb)

    def _to_icon_by_height(self, pil_img, height):
        ratio = height / pil_img.height
        width = max(1, round(pil_img.width * ratio))
        return ImageTk.PhotoImage(pil_img.resize((width, height), Image.LANCZOS))

    def _load_static_images(self):
        for name, px in (("server", SERVER_PX), ("pizza", BASE_PX),
                         ("plate", BASE_PX), ("cupcake", PILE_PX)):
            self._static_icons[name] = self._to_icon(self._open_image(self.image_dir, name), px)
        self._static_icons["counter"] = self._to_icon_by_height(
            self._open_image(self.image_dir, "counter"), COUNTER_H_PX)

    def _topping_icon(self, name):
        if name not in self._topping_icons:
            for base_dir in (self.toppings_dir, self.image_dir):
                path_exists = any(
                    os.path.exists(os.path.join(base_dir, name + s))
                    for s in (".png", ".png.webp", ".webp")
                )
                if path_exists:
                    self._topping_icons[name] = self._to_icon(
                        self._open_image(base_dir, name), TOPPING_PX)
                    break
            else:
                raise FileNotFoundError(
                    f"no image found for topping '{name}' in {self.toppings_dir} or {self.image_dir}")
        return self._topping_icons[name]

    # ------------------------------------------------------------- layout
    def _build(self):
        speech = tk.Frame(self.root, bg=BG)
        speech.pack(padx=20, pady=(18, 6), fill="x")

        server_img = self._static_icons["server"]
        counter_img = self._static_icons["counter"]
        canvas_w = max(server_img.width(), counter_img.width())
        canvas_h = server_img.height()
        server_canvas = tk.Canvas(speech, width=canvas_w, height=canvas_h, bg=BG, highlightthickness=0)
        server_canvas.pack(side="left", padx=(0, 14))
        server_canvas.create_image(canvas_w // 2, canvas_h, anchor="s", image=server_img)
        server_canvas.create_image(canvas_w // 2, canvas_h, anchor="s", image=counter_img)

        self.speech_card = tk.Frame(speech, bg=CARD_BG, relief="solid", bd=1)
        self.speech_card.pack(side="left", fill="x", expand=True)
        self.speech_lbl = tk.Label(self.speech_card, text="", bg=CARD_BG, fg=TEXT,
                                   font=("Helvetica", 14, "bold"), wraplength=SPEECH_WRAP,
                                   justify="left", padx=14, pady=10)
        self.speech_lbl.pack(fill="x")

        self.content = tk.Frame(self.root, bg=BG)
        self.content.pack(padx=20, pady=(4, 20))

    def _make_button(self, parent, text, command, enabled=True):
        bg = BTN_BG if enabled else DISABLED_BG
        fg = TEXT if enabled else DISABLED_FG
        lbl = tk.Label(parent, text=text, bg=bg, fg=fg, font=("Helvetica", 14, "bold"),
                       padx=14, pady=6, bd=4, relief="raised" if enabled else "flat",
                       cursor="hand2" if enabled else "arrow")
        if enabled:
            lbl.bind("<Button-1>", lambda e: command())
            lbl.bind("<Enter>", lambda e: lbl.configure(bg=BTN_ACTIVE))
            lbl.bind("<Leave>", lambda e: lbl.configure(bg=BTN_BG))
        return lbl

    def _set_speech(self, text):
        for w in self.speech_card.winfo_children():
            w.destroy()
        self.speech_lbl = tk.Label(self.speech_card, text=text, bg=CARD_BG, fg=TEXT,
                                   font=("Helvetica", 14, "bold"), wraplength=SPEECH_WRAP,
                                   justify="left", padx=14, pady=10)
        self.speech_lbl.pack(fill="x")

    def _set_speech_need(self, intro, tpk, toppings, outro):
        for w in self.speech_card.winfo_children():
            w.destroy()

        tk.Label(self.speech_card, text=intro, bg=CARD_BG, fg=TEXT, font=("Helvetica", 14, "bold"),
                wraplength=SPEECH_WRAP, justify="left", padx=14).pack(fill="x", pady=(10, 4))

        row = tk.Frame(self.speech_card, bg=CARD_BG)
        row.pack(padx=14, pady=(0, 4))
        for i, name in enumerate(toppings):
            pair = tk.Frame(row, bg=CARD_BG)
            pair.pack(side="left", padx=8)
            tk.Label(pair, text=str(tpk[i]), bg=CARD_BG, fg=TEXT, font=("Helvetica", 16, "bold")).pack(side="left", padx=(0, 4))
            tk.Label(pair, image=self._topping_icon(name), bg=CARD_BG).pack(side="left")

        tk.Label(self.speech_card, text=outro, bg=CARD_BG, fg=TEXT, font=("Helvetica", 14, "bold"),
                wraplength=SPEECH_WRAP, justify="left", padx=14).pack(fill="x", pady=(4, 10))

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _show_and_wait(self):
        self._done.set(0)
        if not self._shown:
            self.root.deiconify()
            self._center_window()
            self._shown = True
        self.root.wait_variable(self._done)

    # ------------------------------------------------------------- display
    def display(self, message):
        if self._closed:
            return
        self._set_speech(message)
        if not self._shown:
            self.root.deiconify()
            self._center_window()
            self._shown = True
        self.root.update_idletasks()

    # ---------------------------------------------------------- askEnough
    def askEnough(self, num_kids, tpk, t_inv, mistakes, toppings, allow_pizza_visual):
        if self._closed:
            return [2] * len(toppings)

        self._eq_toppings = toppings
        self._eq_t_inv = t_inv
        self._eq_mistakes = mistakes
        for i in range(len(toppings)):
            self._enough_selected.setdefault(i, None)

        self._set_speech_need(
            f"There are {num_kids} kids! Each one wants a pizza like this:",
            tpk, toppings,
            f"This is how many of each ingredient we have. Is it enough for {num_kids} pizzas?")

        self._render_enough()
        self._show_and_wait()

        if self._closed:
            return [2] * len(toppings)
        return [self._enough_selected[i] for i in range(len(toppings))]

    def _render_enough(self):
        self._clear_content()
        toppings = self._eq_toppings

        for i, name in enumerate(toppings):
            wrong_last = self._eq_mistakes[i] >= 0 and self._eq_mistakes[i] % 2 == 1
            row = tk.Frame(self.content, bg=BG,
                           highlightbackground=WRONG_BORDER if wrong_last else CARD_BORDER,
                           highlightthickness=3 if wrong_last else 1)
            row.pack(fill="x", pady=4, padx=4)

            tk.Label(row, image=self._topping_icon(name), bg=BG).pack(side="left", padx=(10, 10), pady=8)
            tk.Label(row, text=str(self._eq_t_inv[i]), bg=BG, fg=TEXT,
                    font=("Helvetica", 22, "bold"), width=3).pack(side="left", padx=(0, 14))
            tk.Label(row, text=name.capitalize(), bg=BG, fg=TEXT,
                    font=("Helvetica", 13), width=10, anchor="w").pack(side="left", padx=(0, 14))

            for code, label in ((2, "Just Right"), (0, "Too Much"), (1, "Too Little")):
                selected = self._enough_selected[i] == code
                chip = tk.Label(row, text=label, bg=SELECTED_BG if selected else BTN_BG, fg=TEXT,
                                font=("Helvetica", 12, "bold"), padx=10, pady=6, bd=3,
                                relief="sunken" if selected else "raised", cursor="hand2",
                                highlightbackground=SELECTED_BORDER if selected else BTN_BG,
                                highlightthickness=2)
                chip.pack(side="left", padx=3, pady=8)
                chip.bind("<Button-1>", lambda e, ii=i, cc=code: self._pick_enough(ii, cc))

        all_answered = all(self._enough_selected[i] is not None for i in range(len(toppings)))
        self._make_button(self.content, "Submit", self._submit_enough,
                          enabled=all_answered).pack(pady=(14, 6))

    def _pick_enough(self, i, code):
        self._enough_selected[i] = code
        self._render_enough()

    def _submit_enough(self):
        if any(self._enough_selected[i] is None for i in range(len(self._eq_toppings))):
            return
        self._done.set(1)

    # -------------------------------------------------------------- prompt
    def prompt(self, kids, tpk, t_inv, mistakes, warnings, toppings, allow_pizza_visual, added):
        if self._closed:
            return list(added)

        self._pr_kids = kids
        self._pr_tpk = tpk
        self._pr_t_inv = t_inv
        self._pr_mistakes = mistakes
        self._pr_warnings = warnings
        self._pr_toppings = toppings
        self._pr_visual = allow_pizza_visual
        self._pr_added = list(added)
        self._pr_pizza_counts = {}

        self._pr_adjustable = [i for i in range(len(toppings)) if self._direction(i) != 0]
        if self._focused_topping not in self._pr_adjustable:
            self._focused_topping = self._pr_adjustable[0] if self._pr_adjustable else None

        self._set_speech(f"Let me run to the fridge! How much should I take with me and how much should I bring back for {kids} kids?")
        self._render_prompt()
        self._show_and_wait()

        if self._closed:
            return list(added)
        return list(self._pr_added)

    def _direction(self, i):
        m = self._pr_mistakes[i]
        if m in (0, 1):
            return -1
        if m in (2, 3):
            return 1
        return 0

    def _render_prompt(self):
        self._clear_content()
        toppings = self._pr_toppings

        correct_row = tk.Frame(self.content, bg=BG)
        correct_row.pack(fill="x", pady=(0, 12))
        tk.Label(correct_row, text="Already just right:", bg=BG, fg=TEXT,
                font=("Helvetica", 12, "italic")).pack(side="left", padx=(4, 10))
        for i, name in enumerate(toppings):
            if self._direction(i) == 0:
                tk.Label(correct_row, image=self._topping_icon(name), bg=BG).pack(side="left", padx=4)

        select_row = tk.Frame(self.content, bg=BG)
        select_row.pack(fill="x", pady=(0, 12))
        for i in self._pr_adjustable:
            name = toppings[i]
            focused = i == self._focused_topping
            wrong_last = self._pr_warnings[i] not in (-1, 0)
            border = FOCUS_BORDER if focused else (WRONG_BORDER if wrong_last else BG)
            icon_lbl = tk.Label(select_row, image=self._topping_icon(name),
                                bg=SELECTED_BG if focused else BG,
                                highlightbackground=border, highlightthickness=3, cursor="hand2")
            icon_lbl.pack(side="left", padx=6, pady=4)
            icon_lbl.bind("<Button-1>", lambda e, ii=i: self._focus_topping(ii))

        if self._focused_topping is None:
            tk.Label(self.content, text="Everything's already right!", bg=BG, fg=TEXT,
                    font=("Helvetica", 14, "bold")).pack(pady=20)
            self._make_button(self.content, "Submit", self._submit_prompt).pack(pady=10)
            return

        i = self._focused_topping
        direction = self._direction(i)
        if self._pr_visual and direction > 0:
            self._render_pizza_panel(i)
        else:
            self._render_plain_stepper(i, direction)

        self._make_button(self.content, "Submit", self._submit_prompt).pack(pady=(14, 6))

    def _render_plain_stepper(self, i, direction):
        name = self._pr_toppings[i]
        panel = tk.Frame(self.content, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=2)
        panel.pack(pady=6, padx=6)

        tk.Label(panel, image=self._topping_icon(name), bg=CARD_BG).pack(pady=(12, 4))
        tk.Label(panel, text=f"Have: {self._pr_t_inv[i]}    Per pizza: {self._pr_tpk[i]}",
                bg=CARD_BG, fg=TEXT, font=("Helvetica", 12)).pack(pady=(0, 8))

        self._stepper_row(panel, i, direction)
        tk.Label(panel, text="", bg=CARD_BG, height=1).pack()

    def _magnitude(self, i):
        return abs(self._pr_added[i])

    def _stepper_row(self, parent, i, direction):
        bg = parent["bg"]
        question = ("How many extras do you have that I can take back to the fridge?"
                    if direction < 0 else
                    "How many more should I get you from the fridge?")
        tk.Label(parent, text=question, bg=bg, fg=TEXT, font=("Helvetica", 11, "italic"),
                wraplength=260, justify="center").pack(pady=(0, 4))

        row = tk.Frame(parent, bg=bg)
        row.pack(pady=(0, 12))
        self._make_button(row, "−", lambda: self._bump_magnitude(i, -1)).pack(side="left", padx=10)
        tk.Label(row, text=str(self._magnitude(i)), bg=bg, fg=TEXT,
                font=("Helvetica", 26, "bold"), width=4).pack(side="left")
        self._make_button(row, "+", lambda: self._bump_magnitude(i, 1)).pack(side="left", padx=10)

    def _bump_magnitude(self, i, delta):
        direction = self._direction(i)
        new_mag = max(0, self._magnitude(i) + delta)
        self._pr_added[i] = direction * new_mag
        self._render_prompt()

    def _render_pizza_panel(self, i):
        name = self._pr_toppings[i]
        kids = self._pr_kids
        wanted = self._pr_tpk[i]
        counts = self._pr_pizza_counts.setdefault(i, [0] * kids)
        placed = sum(counts)
        available = max(0, self._pr_t_inv[i] - placed)

        panel = tk.Frame(self.content, bg=BG)
        panel.pack(pady=6)

        tk.Label(panel, image=self._topping_icon(name), bg=BG).pack()
        tk.Label(panel, text=f"{available} {name} available",
                bg=BG, fg=TEXT, font=("Helvetica", 13, "bold")).pack(pady=(4, 8))

        self._make_button(panel, "Add 1 to every pizza", lambda: self._bulk_add(i),
                          enabled=available >= kids).pack(pady=(0, 10))

        grid = tk.Frame(panel, bg=BG)
        grid.pack()
        for k in range(kids):
            cell = tk.Frame(grid, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=2,
                            cursor="hand2")
            cell.grid(row=k // GRID_COLS, column=k % GRID_COLS, padx=6, pady=6)
            img_lbl = tk.Label(cell, image=self._static_icons["pizza"], bg=CARD_BG)
            img_lbl.pack(pady=(6, 2), padx=10)
            count_lbl = tk.Label(cell, text=f"{counts[k]} / {wanted}", bg=CARD_BG, fg=TEXT,
                                 font=("Helvetica", 14, "bold"))
            count_lbl.pack(pady=(0, 6))
            for w in (cell, img_lbl, count_lbl):
                w.bind("<Button-1>", lambda e, kk=k: self._pizza_click(i, kk))

        fallback = tk.Frame(panel, bg=BG)
        fallback.pack(pady=(14, 0))
        self._stepper_row(fallback, i, 1)

    def _pizza_click(self, i, k):
        counts = self._pr_pizza_counts.setdefault(i, [0] * self._pr_kids)
        available = max(0, self._pr_t_inv[i] - sum(counts))
        if available <= 0:
            return
        counts[k] += 1
        self._render_prompt()

    def _bulk_add(self, i):
        kids = self._pr_kids
        counts = self._pr_pizza_counts.setdefault(i, [0] * kids)
        available = max(0, self._pr_t_inv[i] - sum(counts))
        if available < kids:
            return
        for k in range(kids):
            counts[k] += 1
        self._render_prompt()

    def _focus_topping(self, i):
        self._focused_topping = i
        self._pr_pizza_counts.pop(i, None)
        self._render_prompt()

    def _submit_prompt(self):
        self._done.set(1)

    # --------------------------------------------------------------- quest
    def quest(self, text, num_kids, num_cakes, allow_cupcake_visual, plated, pkid, rem):
        if self._closed:
            return 0

        self._set_speech(text)
        self._clear_content()

        if allow_cupcake_visual:
            self._render_cupcake_visual(num_kids, num_cakes, plated, pkid, rem)

        answer_frame = tk.Frame(self.content, bg=BG)
        answer_frame.pack(pady=(16, 4))
        tk.Label(answer_frame, text="Your answer:", bg=BG, fg=TEXT, font=("Helvetica", 13)).pack(side="left", padx=(0, 8))
        self._quest_entry = tk.Entry(answer_frame, font=("Helvetica", 20, "bold"), width=5, justify="center")
        self._quest_entry.pack(side="left")
        self._quest_entry.bind("<Return>", lambda e: self._submit_quest())
        self._quest_entry.focus_set()

        self._make_button(self.content, "Submit", self._submit_quest).pack(pady=(12, 6))

        self._show_and_wait()

        if self._closed:
            return 0
        return self._quest_answer

    def _render_cupcake_visual(self, num_kids, num_cakes, plated, pkid, rem):
        if not plated:
            signature = (num_kids, num_cakes)
            if getattr(self, "_cq_signature", None) != signature:
                self._cq_placed = [0] * num_kids
                self._cq_signature = signature

            available = num_cakes - sum(self._cq_placed)
            tk.Label(self.content, text=f"Cupcakes left to place: {available}",
                    bg=BG, fg=TEXT, font=("Helvetica", 13, "bold")).pack(pady=(0, 8))
            self._make_button(self.content, "Add 1 to every plate",
                              lambda: self._cq_bulk_add(num_kids, num_cakes),
                              enabled=available >= num_kids).pack(pady=(0, 10))

            grid = tk.Frame(self.content, bg=BG)
            grid.pack()
            for k in range(num_kids):
                cell = tk.Frame(grid, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=2,
                                cursor="hand2")
                cell.grid(row=k // GRID_COLS, column=k % GRID_COLS, padx=6, pady=6)
                img_lbl = tk.Label(cell, image=self._static_icons["plate"], bg=CARD_BG)
                img_lbl.pack(pady=(6, 2), padx=8)
                count_lbl = tk.Label(cell, text=str(self._cq_placed[k]), bg=CARD_BG, fg=TEXT,
                                     font=("Helvetica", 14, "bold"))
                count_lbl.pack(pady=(0, 6))
                for w in (cell, img_lbl, count_lbl):
                    w.bind("<Button-1>", lambda e, kk=k: self._cq_click(kk, num_kids, num_cakes))
        else:
            grid = tk.Frame(self.content, bg=BG)
            grid.pack()
            for k in range(num_kids):
                cell = tk.Frame(grid, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=2)
                cell.grid(row=k // GRID_COLS, column=k % GRID_COLS, padx=6, pady=6)
                tk.Label(cell, image=self._static_icons["plate"], bg=CARD_BG).pack(pady=(6, 2), padx=8)
                tk.Label(cell, text=str(pkid), bg=CARD_BG, fg=TEXT, font=("Helvetica", 14, "bold")).pack(pady=(0, 6))

            leftover = tk.Frame(self.content, bg=BG)
            leftover.pack(pady=(14, 0))
            tk.Label(leftover, text="Leftover pile:", bg=BG, fg=TEXT, font=("Helvetica", 12, "italic")).pack()
            pile = tk.Frame(leftover, bg=BG)
            pile.pack()
            for r in range(rem):
                tk.Label(pile, image=self._static_icons["cupcake"], bg=BG).grid(
                    row=r // (GRID_COLS * 2), column=r % (GRID_COLS * 2), padx=2, pady=2)

    def _cq_click(self, k, num_kids, num_cakes):
        available = num_cakes - sum(self._cq_placed)
        if available <= 0:
            return
        self._cq_placed[k] += 1
        self._refresh_quest(num_kids, num_cakes, False, None, None)

    def _cq_bulk_add(self, num_kids, num_cakes):
        available = num_cakes - sum(self._cq_placed)
        if available < num_kids:
            return
        for k in range(num_kids):
            self._cq_placed[k] += 1
        self._refresh_quest(num_kids, num_cakes, False, None, None)

    def _refresh_quest(self, num_kids, num_cakes, plated, pkid, rem):
        text = self.speech_lbl.cget("text")
        typed = self._quest_entry.get() if hasattr(self, "_quest_entry") else ""
        self._clear_content()
        self._render_cupcake_visual(num_kids, num_cakes, plated, pkid, rem)

        answer_frame = tk.Frame(self.content, bg=BG)
        answer_frame.pack(pady=(16, 4))
        tk.Label(answer_frame, text="Your answer:", bg=BG, fg=TEXT, font=("Helvetica", 13)).pack(side="left", padx=(0, 8))
        self._quest_entry = tk.Entry(answer_frame, font=("Helvetica", 20, "bold"), width=5, justify="center")
        self._quest_entry.insert(0, typed)
        self._quest_entry.pack(side="left")
        self._quest_entry.bind("<Return>", lambda e: self._submit_quest())

        self._make_button(self.content, "Submit", self._submit_quest).pack(pady=(12, 6))

    def _submit_quest(self):
        raw = self._quest_entry.get().strip()
        try:
            val = int(raw)
        except ValueError:
            self._quest_entry.configure(highlightbackground=WRONG_BORDER, highlightthickness=2)
            return
        self._quest_answer = val
        self._done.set(1)

    # ------------------------------------------------------------ window
    def _center_window(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 4)}")

    def close(self, delay_ms=0):
        if not self._closed:
            if delay_ms:
                hold = tk.IntVar(value=0)
                self.root.after(delay_ms, lambda: hold.set(1))
                self.root.wait_variable(hold)
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
