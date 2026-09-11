"""Snake Hunt front end for the K-5 pizza-shop math game.

A single Tkinter window that shows a scrollable 10 x 12 board (120 squares,
numbered 1..120 left-to-right then wrapping to the left edge of the next row,
like reading text) and takes its answers from the physical keyboard -- there
is no on-screen keypad. It answers snakehunt.py's two prompts:

  * asktail(place, tail, head)      -- "catch the tail": player types a sign
    (+/-) and a magnitude, then Enter; a + faces the player right, a - flips
    them to face left. Returns the signed delta as an int, exactly like the
    input()-based catch_tail() this replaces.

  * askhead(tail, head, mis_level)  -- "shout the head": player types the
    square number they think the head is on, then Enter. While they're
    guessing, the board's real 10 x 12 grid is swapped out for a single
    centered line holding just the player (at the snake's tail) and the
    snake's own tiles -- so they can see its shape and length, but not any
    square's board number (numbers stay hidden here), and the line is
    deliberately decoupled from the real grid so board-position tricks
    can't be used to shortcut the addition/subtraction. Right after they
    confirm, a buddy marker appears on that same line, on the tile they
    guessed, so they can see whether it lines up with the head -- the view
    stays on this line the whole time; it never jumps out to the real grid.
    A wrong guess leaves a small number in that square's corner, visible on
    the retry, so they can see what they already tried. Returns the guessed
    square as an int.

  * moveplayer(player_place)        -- called after snakehunt.py resolves
    the player's move (which may differ from what they asked for, e.g. if
    checkplace() reverted it) to redraw the player token at its real spot.

Only the player's own square ever shows a number (in the bubble above their
token), so a child always knows where they are without the board being
cluttered with numbers everywhere. The snake's squares reveal their own
numbers too, but only once mis_level (the catch_head_mistake_level, wired in
from snakehunt.py) rises above 1.

Usage from snakehunt.py:

    from snake_ui import SnakeHuntUI
    ui = SnakeHuntUI(image_dir="snakeimages")
    delta = ui.asktail(place, tail, head)
    ...
    ui.moveplayer(new_place)
    ...
    guess = ui.askhead(tail, head, mistake_level, snake_len)
    ...
    ui.close()
"""

import os
import tkinter as tk

from PIL import Image, ImageTk

BOARD_COLS = 10
BOARD_ROWS = 12
BOARD_SQUARES = BOARD_COLS * BOARD_ROWS  # 120
VISIBLE_ROWS = 6           # rows shown before the board needs to scroll
MAX_DIGITS = 3             # squares only go up to 120
HEAD_REVEAL_MS = 600      # how long the buddy marker holds before the next question
SNAKE_HIT_MS = 250        # how long the player holds on a snake hit before snapping back
LINE_MAX_COLS = 11        # widest a snake's tail-to-head line can be (max snake_len + 1)

CELL = 54
BADGE_H = 26               # header strip above each tile, for the player's location bubble
COL_GAP = 2                # small horizontal gap between squares in a row
ROW_GAP = 10                # bigger vertical gap -- "rows slightly separated"

BG = "#eef3fb"
TILE_GROUP_SIZE = 5     # tiles per color band
TILE_COLORS = [         # cycles every 4 bands (20 tiles), then repeats
    "#dde9fc",          # soft blue
    "#dcf5e0",          # soft green
    "#fdecc8",          # soft peach
    "#f6dced",          # soft pink
]
CELL_BORDER = "#9fb6d9"
PLAYER_CELL = "#fff3c4"
TEXT = "#233047"
ACCENT = "#2f6fed"
TAIL_ACCENT = "#3aa655"    # the tail's own location bubble, kept distinct from the player's


class SnakeHuntUI:
    def __init__(self, image_dir="snakeimages"):
        self.image_dir = image_dir

        self.root = tk.Tk()
        self.root.title("Snake Hunt")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._done = tk.IntVar(value=0)
        self._answer = None
        self._closed = False
        self._shown = False

        self.mode = None            # "tail" or "head"
        self.player_place = 1
        self.snake_tail = None
        self.snake_head = None
        self.show_snake_numbers = False
        self.sign = 1               # +1 faces right, -1 faces left
        self.digits = ""            # magnitude (tail) or guess (head), as text
        self.guess_square = None    # set only once a head guess is confirmed
        self._input_locked = False  # true while a confirmed guess is being shown
        self.wrong_guesses = set()  # squares already guessed wrong for this snake

        self._imgs = {}
        self._square_canvases = {}

        self._load_images()
        self._build()
        self.root.withdraw()   # stays hidden until the first asktail/askhead

    # ------------------------------------------------------------- images
    def _load_images(self):
        def load(name, flip=False):
            path = os.path.join(self.image_dir, f"{name}.png")
            img = Image.open(path).convert("RGBA")
            img.thumbnail((CELL - 10, CELL - 10), Image.LANCZOS)
            if flip:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            return ImageTk.PhotoImage(img)

        self._imgs["player_right"] = load("player")
        self._imgs["player_left"] = load("player", flip=True)
        self._imgs["head"] = load("head")
        self._imgs["tail"] = load("tail")            # points right, away from a head to its left
        self._imgs["tail_flip"] = load("tail", flip=True)  # away from a head to its right
        self._imgs["body"] = load("body")
        self._imgs["buddy"] = load("buddy")

    # ------------------------------------------------------------- layout
    def _build(self):
        self.title_lbl = tk.Label(self.root, text="", bg=BG, fg=TEXT,
                                  font=("Helvetica", 22, "bold"))
        self.title_lbl.pack(pady=(16, 2))

        # One slot, two mutually-exclusive occupants: sub_lbl (askhead's
        # instructional text) or tail_header (catch-the-tail's big numbers).
        # Keeping them both as children of this one always-packed slot means
        # toggling which is shown never disturbs the rest of the window's
        # top-to-bottom order.
        self.header_slot = tk.Frame(self.root, bg=BG)
        self.header_slot.pack(pady=(0, 10))

        self.sub_lbl = tk.Label(self.header_slot, text="", bg=BG, fg=ACCENT,
                                font=("Helvetica", 40), wraplength=560,
                                justify="center")
        self.sub_lbl.pack()

        self._build_tail_header()
        self._build_board()
        self._build_controls()

        self.root.bind("<Return>", lambda e: self._confirm())
        self.root.bind("<BackSpace>", lambda e: self._backspace())
        self.root.bind("<Escape>", lambda e: self._clear())
        for d in "0123456789":
            self.root.bind(d, lambda e, d=d: self._press_digit(d))
        self.root.bind("<plus>", lambda e: self._set_sign(1))
        self.root.bind("<equal>", lambda e: self._set_sign(1))
        self.root.bind("<Right>", lambda e: self._set_sign(1))
        self.root.bind("<minus>", lambda e: self._set_sign(-1))
        self.root.bind("<Left>", lambda e: self._set_sign(-1))

    def _build_tail_header(self):
        """Catch-the-tail's header: player_place and the +/- input sit side
        by side as one expression -- "10" next to "+5" reads as "10 + 5".
        The tail's own location isn't spelled out here at all; it gets its
        own bubble on the board instead (see _draw_place_bubble)."""
        self.tail_header = tk.Frame(self.header_slot, bg=BG)

        self.player_num_lbl = tk.Label(self.tail_header, text="", bg=BG, fg=TEXT,
                                       font=("Helvetica", 44, "bold"))
        self.player_num_lbl.pack(side="left")
        self.tail_readout = tk.Label(self.tail_header, text="_", bg=BG, fg=ACCENT,
                                     font=("Helvetica", 44, "bold"), padx=2)
        self.tail_readout.pack(side="left")

    def _build_board(self):
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(padx=16, pady=4)

        board_w = max(BOARD_COLS, LINE_MAX_COLS) * (CELL + COL_GAP) + 24
        board_h = VISIBLE_ROWS * (CELL + BADGE_H + ROW_GAP) + 16

        self.canvas = tk.Canvas(wrap, width=board_w, height=board_h,
                                bg=BG, highlightthickness=0)
        vbar = tk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vbar.set)
        self.canvas.pack(side="left")
        vbar.pack(side="left", fill="y")

        self.board = tk.Frame(self.canvas, bg=BG)
        self._board_window = self.canvas.create_window(
            (0, 0), window=self.board, anchor="nw")
        self.board.bind("<Configure>", lambda e: self._sync_board_window())
        self.canvas.bind("<Enter>", lambda e: self._bind_wheel())
        self.canvas.bind("<Leave>", lambda e: self._unbind_wheel())

        for n in range(1, BOARD_SQUARES + 1):
            r, c = self._square_rc(n)
            # each cell is taller than one square: a blank header strip on
            # top (where the player's location bubble can pop up) plus the
            # actual CELL x CELL tile below it
            cell = tk.Canvas(self.board, width=CELL, height=CELL + BADGE_H,
                             bg=BG, highlightthickness=0)
            cell.grid(row=r, column=c, padx=COL_GAP // 2, pady=ROW_GAP // 2)
            self._square_canvases[n] = cell

    def _build_controls(self):
        # No on-screen keypad -- answers come from the physical keyboard
        # (digit keys, +/-, Backspace, Enter). This readout is just feedback
        # for what's been typed so far -- used for askhead; catch-the-tail's
        # input instead shows inline as part of the tail_header expression.
        self.controls_panel = tk.Frame(self.root, bg=BG)
        self.controls_panel.pack(pady=(6, 20))

        self.readout = tk.Label(self.controls_panel, text="_", bg="white", fg=TEXT,
                                font=("Helvetica", 34, "bold"), width=5,
                                relief="sunken", bd=3)
        self.readout.pack()

    # ------------------------------------------------------------ geometry
    def _square_rc(self, n):
        idx = n - 1
        row = idx // BOARD_COLS
        col = idx % BOARD_COLS       # every row starts fresh at the left edge
        return row, col

    def _layout_full_board(self):
        """Every square back at its real row/column on the 10 x 12 grid."""
        for n, cell in self._square_canvases.items():
            r, c = self._square_rc(n)
            cell.grid(row=r, column=c, padx=COL_GAP // 2, pady=ROW_GAP // 2)

    def _layout_line(self, span):
        """Just the given squares, in order, on one row -- detached from
        their real board position so it can't be used to shortcut the
        head-guessing math. _sync_board_window() centers this row (both
        ways) in the visible canvas afterward."""
        span = list(span)
        span_set = set(span)
        total_cols = max(BOARD_COLS, LINE_MAX_COLS)
        offset = max(0, (total_cols - len(span)) // 2)
        for i, n in enumerate(span):
            self._square_canvases[n].grid(row=0, column=offset + i,
                                          padx=COL_GAP // 2, pady=ROW_GAP // 2)
        for n, cell in self._square_canvases.items():
            if n not in span_set:
                cell.grid_remove()

    def _sync_board_window(self):
        """Keep the board's placement in the canvas matching the current
        mode: dead-centered (both axes) for the single-line head-guess view
        (which stays up through the post-confirm buddy reveal too), or
        pinned top-left with normal scrolling for the full board."""
        line_mode = self.mode == "head"
        self.canvas.update_idletasks()
        if line_mode:
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            self.canvas.coords(self._board_window, cw / 2, ch / 2)
            self.canvas.itemconfigure(self._board_window, anchor="center")
            self.canvas.configure(scrollregion=(0, 0, cw, ch))
        else:
            self.canvas.coords(self._board_window, 0, 0)
            self.canvas.itemconfigure(self._board_window, anchor="nw")
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_wheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_wheel(self):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        delta = event.delta
        if abs(delta) >= 120:
            delta //= 120
        self.canvas.yview_scroll(int(-delta), "units")

    def _scroll_to_square(self, n):
        self.root.update_idletasks()
        if self.mode == "head":
            # collapsed to one line the whole time we're guessing the head
            # (guess and reveal alike) -- nothing to scroll to
            self.canvas.yview_moveto(0)
            return
        row, _ = self._square_rc(n)
        total = max(1, BOARD_ROWS - 1)
        frac = max(0.0, min(1.0, row / total - 0.15))
        self.canvas.yview_moveto(frac)

    def _center_window(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 4)}")

    # -------------------------------------------------------------- input
    def _press_digit(self, d):
        if self._input_locked or len(self.digits) >= MAX_DIGITS:
            return
        self.digits += d
        self._update_readout()

    def _backspace(self):
        if self._input_locked:
            return
        self.digits = self.digits[:-1]
        self._update_readout()

    def _clear(self):
        if self._input_locked:
            return
        self.digits = ""
        self._update_readout()

    def _set_sign(self, s):
        if self._input_locked or self.mode != "tail":
            return
        self.sign = s
        self._update_readout()

    def _update_readout(self):
        if self.mode == "tail":
            sign_txt = "+" if self.sign >= 0 else "-"
            self.readout.configure(text=f"{sign_txt}{self.digits or '_'}")
            self._update_tail_header()
        else:
            self.readout.configure(text=self.digits or "_")
        self._render_board()

    def _update_tail_header(self):
        sign_txt = "+" if self.sign >= 0 else "-"
        self.tail_readout.configure(text=f"{sign_txt}{self.digits or '_'}")
        self.player_num_lbl.configure(text=str(self.player_place))

    def _confirm(self):
        if self._input_locked or not self.digits:
            return
        if self.mode == "tail":
            self._answer = self.sign * int(self.digits)
            self._done.set(1)
        elif self.mode == "head":
            self._answer = int(self.digits)
            if self._answer != self.snake_head:
                self.wrong_guesses.add(self._answer)
            # Drop the buddy marker on the guessed tile, right there on the
            # same line, and hold it visible for a beat before the next
            # question (right or wrong) replaces it -- the view never jumps
            # out to the full board for this.
            self.guess_square = self._answer
            self._input_locked = True
            self._render_board()
            self.root.after(HEAD_REVEAL_MS, self._release_after_head_guess)

    def _release_after_head_guess(self):
        self._done.set(1)

    # ---------------------------------------------------------------- API
    def asktail(self, place, tail, head):
        """'Catch the tail': returns the signed delta the player entered."""
        if self._closed:
            return 0

        self.mode = "tail"
        self.player_place = place
        self.snake_tail = tail
        self.snake_head = head
        self.show_snake_numbers = False  # never hinted during catch-the-tail
        self.digits = ""
        self.wrong_guesses = set()  # starting a new snake -- clear past head guesses

        self.title_lbl.configure(text=f"Catch the tail at {tail}!")
        self.sub_lbl.pack_forget()
        self.tail_header.pack()
        self.controls_panel.pack_forget()

        return self._run_round() or 0

    def askhead(self, tail, head, mis_level, snake_len=None):
        """'Shout the head': returns the square the player guessed."""
        if self._closed:
            return None

        self.mode = "head"
        self.player_place = tail
        self.snake_tail = tail
        self.snake_head = head
        self.show_snake_numbers = mis_level > 1
        self.digits = ""
        self.guess_square = None

        self.title_lbl.configure(text="Where's the head?")
        self.tail_header.pack_forget()
        self.sub_lbl.configure(text="")
        self.sub_lbl.pack()
        self.controls_panel.pack(pady=(6, 20))

        return self._run_round()

    def moveplayer(self, player_place):
        """Redraw the player token at its real (snakehunt.py-resolved) square.

        If this move lands on the snake but not its tail (a hit), the player
        token holds there, visibly, for a beat before returning -- so the
        child sees what happened before snakehunt.py's next moveplayer()
        call snaps them back to their previous square.
        """
        if self._closed:
            return
        self.player_place = player_place
        if self.mode == "tail":
            self._update_tail_header()
        self._render_board()
        self._scroll_to_square(player_place)

        if self._is_snake_hit(player_place) or player_place == self.snake_tail:
            self._pause(SNAKE_HIT_MS)

    def _is_snake_hit(self, place):
        if self.snake_tail is None or self.snake_head is None:
            return False
        lo, hi = sorted((self.snake_tail, self.snake_head))
        return lo <= place <= hi and place != self.snake_tail

    def _pause(self, ms):
        if self._closed:
            return
        hold = tk.IntVar(value=0)
        self.root.after(ms, lambda: hold.set(1))
        self.root.wait_variable(hold)

    def close(self):
        if not self._closed:
            self._closed = True
            try:
                self.root.destroy()
            except tk.TclError:
                pass

    # ------------------------------------------------------------ internals
    def _run_round(self):
        self._answer = None
        self._input_locked = False
        self._done.set(0)
        self._update_readout()

        if not self._shown:
            self.root.deiconify()
            self._center_window()
            self._shown = True

        self._render_board()
        self._scroll_to_square(self.player_place)
        self.root.wait_variable(self._done)
        return self._answer

    def _render_board(self):
        tile_mid = BADGE_H + CELL / 2   # vertical center of the tile, below the badge strip

        # Guessing the head (before AND after confirming -- the buddy marker
        # lands right on this same line, it never jumps to the real grid)
        # swaps the real grid for a single centered line holding just the
        # player (at the snake's tail) and the snake's own tiles, detached
        # from the real board position so it can't be used to shortcut the
        # math. The real grid is only used during catch-the-tail.
        line_mode = self.mode == "head"
        have_snake = self.snake_tail is not None and self.snake_head is not None
        if line_mode and have_snake:
            lo, hi = sorted((self.snake_tail, self.snake_head))
            self._layout_line(range(lo, hi + 1))
        else:
            self._layout_full_board()
        self._sync_board_window()

        for cell in self._square_canvases.values():
            cell.delete("all")
        for n, cell in self._square_canvases.items():
            band = (n - 1) // TILE_GROUP_SIZE % len(TILE_COLORS)
            cell.create_rectangle(0, BADGE_H, CELL, BADGE_H + CELL,
                                  fill=TILE_COLORS[band], outline=CELL_BORDER, width=1)

        if have_snake:
            lo, hi = sorted((self.snake_tail, self.snake_head))
            for n in range(lo, hi + 1):
                cell = self._square_canvases[n]
                if n == self.snake_head:
                    img = self._imgs["head"]
                elif n == self.snake_tail:
                    # point away from wherever the head currently is
                    img = (self._imgs["tail_flip"] if self.snake_head > self.snake_tail
                           else self._imgs["tail"])
                else:
                    img = self._imgs["body"]
                cell.create_image(CELL / 2, tile_mid, image=img)
                # hint numbers are a "shout the head" aid only -- never during catch-the-tail
                if self.mode == "head" and self.show_snake_numbers:
                    cell.create_text(CELL - 9, BADGE_H + 9, text=str(n),
                                     font=("Helvetica", 9, "bold"), fill=TEXT)

            # the tail gets its own location bubble too, just like the
            # player -- but only while it's still a distinct square to chase
            # (during askhead the player is already standing on it)
            if self.mode == "tail" and self.snake_tail != self.player_place:
                tail_cell = self._square_canvases.get(self.snake_tail)
                if tail_cell:
                    self._draw_place_bubble(tail_cell, self.snake_tail, color=TAIL_ACCENT)

        if self.mode == "head":
            # a wrong guess leaves its number in the corner of that square,
            # visible on a later attempt if it's still on screen
            for n in self.wrong_guesses:
                cell = self._square_canvases.get(n)
                if cell:
                    cell.create_text(9, BADGE_H + 9, text=str(n),
                                     font=("Helvetica", 9, "bold"), fill=TEXT)

        if self.mode == "head" and self.guess_square:
            cell = self._square_canvases.get(self.guess_square)
            if cell:
                cell.create_image(CELL / 2, tile_mid, image=self._imgs["buddy"])

        if self.player_place:
            cell = self._square_canvases.get(self.player_place)
            if cell:
                cell.create_rectangle(0, BADGE_H, CELL, BADGE_H + CELL,
                                      fill=PLAYER_CELL, outline=CELL_BORDER, width=1)
                img = self._imgs["player_right"] if self.sign >= 0 else self._imgs["player_left"]
                cell.create_image(CELL / 2, tile_mid, image=img)
                self._draw_place_bubble(cell, self.player_place)

    def _draw_place_bubble(self, cell, place, color=ACCENT):
        # a big speech bubble above a token, saying where it is -- used for
        # the player always, and for the tail during catch-the-tail
        cx = CELL / 2
        bw, bh = 40, 18
        top, bottom = 1, 1 + bh
        cell.create_oval(cx - bw / 2, top, cx + bw / 2, bottom,
                         fill="white", outline=color, width=2)
        cell.create_polygon(cx - 5, bottom - 3, cx + 5, bottom - 3, cx, bottom + 6,
                            fill="white", outline=color)
        cell.create_text(cx, (top + bottom) / 2, text=str(place),
                         font=("Helvetica", 15, "bold"), fill=color)

    def _on_close(self):
        self._answer = None
        self._closed = True
        self._done.set(1)
        try:
            self.root.destroy()
        except tk.TclError:
            pass


if __name__ == "__main__":
    # Quick standalone demo: python3 snake_ui.py
    ui = SnakeHuntUI(image_dir="snakeimages")
    try:
        place, tail, head, mis = 1, 14, 20, 0
        delta = ui.asktail(place, tail, head)
        print("tail delta:", delta)
        ui.moveplayer(max(1, min(60, place + delta)))
        guess = ui.askhead(tail, head, mis, snake_len=head - tail)
        print("head guess:", guess)
    finally:
        ui.close()
