"""One shared, permanently-hidden Tk root for the whole game process.

Tkinter's macOS/Aqua backend ties its NSApplication and window-manager
integration (Dock reactivation events, menu bar, etc.) to the FIRST
tk.Tk() interpreter created in a process, and assumes exactly one exists
for the process's whole lifetime. Destroying that root and later creating
a new tk.Tk() -- which is otherwise a tempting way to give each minigame
window its own independent lifecycle -- segfaults the next time macOS's
Aqua layer touches the now-destroyed interpreter (e.g. on the next window
activation), because internal handlers like handleReopenApplicationEvent
still point at it.

So every *_ui.py in this project creates its window as a tk.Toplevel()
of the ONE shared root returned here, instead of its own tk.Tk(). Each
Toplevel can still be freely created and destroyed on its own (that's
what actually fixes the earlier "stacked Tk() roots load images into the
wrong interpreter" bug), while exactly one real Tk interpreter stays
alive for the life of the process, which is what Tk/Aqua actually
supports.
"""

import tkinter as tk

_root = None


def get_shared_root():
    global _root
    if _root is None:
        _root = tk.Tk()
        _root.withdraw()
    return _root
