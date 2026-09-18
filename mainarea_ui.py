"""Main hub front end for nerdygamemain.py.

A single Tkinter window (reused for the whole session) with a background
image, an "Up Next" box that always shows the next two tasks in the
backend's task queue, and a note area used for the shopkeeper's messages
and the occasional confirmation button.

Usage from nerdygamemain.py:

    from mainarea_ui import MainUI

    ui = MainUI(image_dir="mainimages")
    ui.updateTasks(taskqueue)   # non-blocking, refreshes the "Up Next" box
    ui.note("some message", 0) # blocks until "Let's go!" is clicked
    ui.note("some message", 1) # blocks until "Hire Employee" is clicked,
                                # then lingers on "+1 employee!!" briefly
"""

import os
import tkinter as tk

from PIL import Image, ImageTk

WINDOW_W = 960
WINDOW_H = 720

BG = "#fdf6e3"
TEXT = "#3b2f1e"
BOX_BG = "#ffffff"
BOX_BORDER = "#3b2f1e"
BTN_BG = "#ffd27f"
BTN_ACTIVE = "#ffbe4d"

HIRE_LINGER_MS = 500

TASK_LABELS = {
    "grocshop": "Go Grocery Shopping",
    "snakehunt": "Hunt for Snakes",
    "cointradem": "Pay for Groceries",
    "cointradep": "Count Your Earnings",
    "party": "Host a Pizza Party",
    "slice": "Serve Pizza Slices",
}


class MainUI:
    def __init__(self, image_dir="mainimages"):
        self.image_dir = image_dir

        self.root = tk.Tk()
        self.root.title("Nerdy Game")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._done = tk.IntVar(value=0)
        self._closed = False
        self._shown = False

        self._build()
        self.root.withdraw()

    # ------------------------------------------------------------------ build
    def _build(self):
        bg_path = os.path.join(self.image_dir, "background.png")
        bg_img = Image.open(bg_path).convert("RGBA").resize(
            (WINDOW_W, WINDOW_H), Image.LANCZOS)
        self._bg_photo = ImageTk.PhotoImage(bg_img)
        tk.Label(self.root, image=self._bg_photo, bd=0).place(
            x=0, y=0, width=WINDOW_W, height=WINDOW_H)

        tasks_box, tasks_content = self._build_titled_box(self.root, "Up Next")
        tasks_box.place(relx=0.5, y=24, anchor="n")

        self.task1_label = tk.Label(tasks_content, text="", bg=BOX_BG, fg=TEXT,
                                    font=("Helvetica", 15, "bold"), justify="left")
        self.task1_label.pack(anchor="w")
        self.task2_label = tk.Label(tasks_content, text="", bg=BOX_BG, fg=TEXT,
                                    font=("Helvetica", 15, "bold"), justify="left")
        self.task2_label.pack(anchor="w")

        note_box, note_content = self._build_titled_box(self.root, "")
        note_box.place(relx=0.5, rely=0.62, anchor="center")

        self.message_label = tk.Label(note_content, text="", bg=BOX_BG, fg=TEXT,
                                      font=("Helvetica", 16, "bold"), wraplength=560,
                                      justify="center")
        self.message_label.pack(pady=(0, 12))

        self.button_frame = tk.Frame(note_content, bg=BOX_BG)
        self.button_frame.pack()

    def _build_titled_box(self, parent, title, title_font_size=15):
        """An off-white bordered box with a bold title at top. Returns
        (box, content) -- pack `box` wherever it goes, and put children in
        `content`."""
        box = tk.Frame(parent, bg=BOX_BG, highlightbackground=BOX_BORDER,
                       highlightthickness=2)
        if title:
            tk.Label(box, text=title, bg=BOX_BG, fg=TEXT,
                    font=("Helvetica", title_font_size, "bold")).pack(pady=(10, 6), padx=16)
        content = tk.Frame(box, bg=BOX_BG)
        content.pack(padx=20, pady=(0, 16))
        return box, content

    def _make_button(self, parent, text, command):
        lbl = tk.Label(parent, text=text, bg=BTN_BG, fg=TEXT, font=("Helvetica", 15, "bold"),
                       padx=16, pady=8, bd=4, relief="raised", cursor="hand2")
        lbl.bind("<Button-1>", lambda e: command())
        lbl.bind("<Enter>", lambda e: lbl.configure(bg=BTN_ACTIVE))
        lbl.bind("<Leave>", lambda e: lbl.configure(bg=BTN_BG))
        return lbl

    # ---------------------------------------------------------------- tasks
    def _task_label(self, name):
        return TASK_LABELS.get(name, name)

    def updateTasks(self, taskqueue):
        if self._closed:
            return
        upcoming = list(taskqueue)
        first = self._task_label(upcoming[0]) if len(upcoming) > 0 else "(all done!)"
        second = self._task_label(upcoming[1]) if len(upcoming) > 1 else ""

        self.task1_label.configure(text=f"1. {first}")
        self.task2_label.configure(text=f"2. {second}" if second else "")
        self._show()

    # ----------------------------------------------------------------- note
    def note(self, text, code):
        if self._closed:
            return

        self.message_label.configure(text=text)
        for w in self.button_frame.winfo_children():
            w.destroy()

        if code == 0:
            btn = self._make_button(self.button_frame, "Let's go!", lambda: self._done.set(1))
            btn.pack()
        elif code == 1:
            btn = self._make_button(self.button_frame, "Hire Employee", lambda: None)
            btn.pack()

            def _clicked():
                btn.unbind("<Button-1>")
                btn.configure(text="+1 employee!!", bg=BTN_ACTIVE)
                self._pause(HIRE_LINGER_MS)
                self._done.set(1)

            btn.bind("<Button-1>", lambda e: _clicked())
        else:
            self._show()
            return

        self._done.set(0)
        self._show()
        self.root.wait_variable(self._done)

        if self._closed:
            return
        try:
            btn.destroy()
        except tk.TclError:
            pass

    def close(self):
        if not self._closed:
            self._closed = True
            try:
                self.root.destroy()
            except tk.TclError:
                pass

    # ------------------------------------------------------------ internals
    def _show(self):
        if not self._shown:
            self.root.deiconify()
            self._center_window()
            self._shown = True

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
