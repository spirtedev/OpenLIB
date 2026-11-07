"""Small GUI-only helpers (kept separate from helpers.py, which is backend)."""
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import database
from permissions import has_permission
from status_codes import Status
from theme import *

try:
    from PIL import Image, ImageTk
except ImportError:  # Pillow not installed: pages fall back to plain text
    Image = None

# The assets folder sits next to this file, whatever directory the app is launched from
ASSETS_DIR = Path(__file__).parent / "assets"


def load_image(filename, max_width, max_height):
    """
    Load an image from the assets folder and shrink it to fit inside
    max_width x max_height. The aspect ratio is kept (no distortion) and
    the image is never enlarged.
    Returns a PhotoImage, or None if the file or Pillow is missing.

    IMPORTANT: the caller must store the result (e.g. self.logo_image = ...),
    otherwise Tkinter garbage-collects it and the image disappears.
    """
    path = ASSETS_DIR / filename
    # When an image cannot be shown, the pages display a text title instead.
    # These messages (printed in the console) explain the reason.
    if Image is None:
        print("OpenLIB: Pillow is not installed, so images are not shown. Fix: pip install pillow")
        return None
    if not path.exists():
        print(f"OpenLIB: image not found: {path}")
        print("         Put it in the 'assets' folder that sits next to main.py.")
        return None
    try:
        image = Image.open(path)
        scale = min(max_width / image.width, max_height / image.height, 1)
        new_size = (int(image.width * scale), int(image.height * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    except Exception as error:
        print(f"OpenLIB: could not load image {path}: {error}")
        return None


# WINDOW HELPERS


def center_window(window, width, height):
    """
    Sets the size of a window and places it in the middle of the screen.
    Parameters: window (the main window or a Toplevel), width and height in pixels.
    """
    x = (window.winfo_screenwidth() - width) // 2   # left edge
    y = (window.winfo_screenheight() - height) // 2  # top edge
    window.geometry(f"{width}x{height}+{x}+{y}")


# BUTTONS AND TABLES


def make_button(parent, text, command):
    """
    Creates a gold button in the application style (the caller places it with pack/grid).
    Parameters: parent widget, button text, command = the function called on click.
    Returns the Button.
    """
    return tk.Button(parent, text=text, command=command, font=FONT, bg=GOLD_COLOR,
                     fg=DARK_TEXT, relief="flat", cursor="hand2", padx=10, pady=3)


def make_table(parent, columns):
    """
    Creates a table (ttk.Treeview) with a vertical scroll bar.
    Parameters: parent widget, columns = list of (heading, width) pairs.
    Returns (frame, table): the caller must pack the FRAME and fills the TABLE:
        table.insert("", "end", iid="5", values=(...))   # iid = the record id
        table.selection()                                 # -> ("5",) the clicked row
    Rows inserted with tags=("overdue",) are shown in red.
    """
    frame = tk.Frame(parent, bg=APP_BG)

    column_names = [heading for heading, width in columns]
    table = ttk.Treeview(frame, columns=column_names, show="headings", selectmode="browse")
    for heading, width in columns:
        table.heading(heading, text=heading)
        table.column(heading, width=width, minwidth=50, anchor="w")
    table.tag_configure("overdue", foreground=ERROR_COLOR)

    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    table.pack(side="left", fill="both", expand=True)
    return frame, table


def clear_table(table):
    """Removes every row from a table."""
    table.delete(*table.get_children())


def selected_id(table, what):
    """
    Returns the id (int) of the row the user clicked in a table.
    If nothing is selected, shows a message and returns None.
    Parameters: table, what = a word for the message (e.g. "book").
    """
    selection = table.selection()
    if not selection:
        messagebox.showinfo("Select a row", f"Please click a {what} in the list first.")
        return None
    return int(selection[0])


# PERMISSIONS


def user_is_allowed(controller, action):
    """
    Checks (against the DATABASE, not against what is on screen) that the logged-in
    user may do `action`. Shows an error message and returns False if not.
    Parameters: controller (the main app), action (a key of permissions.PERMISSIONS).
    """
    current = controller.current_user
    if current is None:
        return False

    fresh = database.get_user(current["id"])
    if isinstance(fresh, Status):
        messagebox.showerror("Account not found", "Your account no longer exists.")
        return False

    controller.current_user["role"] = fresh["role"]  # keep the stored role up to date
    if has_permission(fresh["role"], action):
        return True

    messagebox.showerror("Not allowed", "You do not have permission to do this.")
    return False


# BACKGROUND WORK


def run_in_background(widget, work, when_done):
    """
    Runs a slow function in a second thread so the window does not freeze.
    Used only for password hashing (takes a moment on purpose).

    Parameters:
      widget    - any widget of the page (used to schedule the checks)
      work      - function with no arguments. RULE: it must not touch Tkinter widgets
                  or the database, it may only calculate and return a value.
      when_done - function(result, error) called in the normal GUI thread when the work
                  has finished. `error` is None unless work() crashed.
    """
    outcome = {}  # the worker thread writes the result here

    def worker():
        try:
            outcome["result"] = work()
            outcome["error"] = None
        except Exception as error:  # report any problem back to the GUI
            outcome["result"] = None
            outcome["error"] = error
        outcome["finished"] = True

    def check_if_finished():
        try:
            if not widget.winfo_exists():
                return  # the page was closed while waiting: nothing to update
            if outcome.get("finished"):
                when_done(outcome["result"], outcome["error"])
            else:
                widget.after(50, check_if_finished)  # look again in 50 milliseconds
        except tk.TclError:
            return

    threading.Thread(target=worker, daemon=True).start()
    check_if_finished()
