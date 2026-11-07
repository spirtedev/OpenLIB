import tkinter as tk
from tkinter import ttk, messagebox
import database
from helpers import GENRES, MAX_BOOK_QUANTITY, get_status_message, to_whole_number
from gui_helpers import make_button, center_window, user_is_allowed
from status_codes import Status
from theme import *


class BookForm(tk.Toplevel):
    """
    A small pop-up window to add a new book or to edit an existing one.
    Parameters:
      parent   - the page that opens the form
      controller - the main app
      book     - None to ADD a book, or a book row to EDIT it
      on_saved - function called after a successful save (the page uses it to refresh its table)
    """

    def __init__(self, parent, controller, book=None, on_saved=None):
        super().__init__(parent)
        self.controller = controller
        self.book = book
        self.on_saved = on_saved

        # NOTE: do not store anything in self.title, it would hide the window's title() method
        self.title("Add Book" if book is None else "Edit Book")
        self.configure(bg=APP_BG, padx=20, pady=15)
        self.resizable(False, False)

        # Everything in this window is placed with grid(): column 0 = labels, column 1 = fields
        tk.Label(self, text="Title *", font=FONT, bg=APP_BG, fg=DARK_TEXT).grid(row=0, column=0, sticky="w", pady=6)
        self.title_entry = tk.Entry(self, width=36, font=FONT)
        self.title_entry.grid(row=0, column=1, pady=6, ipady=3)

        tk.Label(self, text="Author", font=FONT, bg=APP_BG, fg=DARK_TEXT).grid(row=1, column=0, sticky="w", pady=6)
        self.author_entry = tk.Entry(self, width=36, font=FONT)
        self.author_entry.grid(row=1, column=1, pady=6, ipady=3)

        tk.Label(self, text="Genre *", font=FONT, bg=APP_BG, fg=DARK_TEXT).grid(row=2, column=0, sticky="w", pady=6)
        self.genre_box = ttk.Combobox(self, values=GENRES, state="readonly", width=33)
        self.genre_box.grid(row=2, column=1, sticky="w", pady=6)

        tk.Label(self, text="Copies in stock *", font=FONT, bg=APP_BG, fg=DARK_TEXT
                 ).grid(row=3, column=0, sticky="w", pady=6)
        self.quantity_entry = tk.Spinbox(self, from_=0, to=MAX_BOOK_QUANTITY, width=10, font=FONT)
        self.quantity_entry.grid(row=3, column=1, sticky="w", pady=6, ipady=3)

        buttons = tk.Frame(self, bg=APP_BG)
        buttons.grid(row=4, column=0, columnspan=2, pady=(15, 0))
        make_button(buttons, "Save", self.save).pack(side="left", padx=6)
        make_button(buttons, "Cancel", self.destroy).pack(side="left", padx=6)

        # When editing, fill the fields with the current values of the book
        if book is not None:
            self.title_entry.insert(0, book["title"])
            self.author_entry.insert(0, book["author"] or "")
            self.genre_box.set(book["genre"])
            self.quantity_entry.delete(0, tk.END)
            self.quantity_entry.insert(0, str(book["quantity"]))

        center_window(self, 520, 290)
        self.transient(parent.winfo_toplevel())  # stays on top of the main window
        self.grab_set()                          # the main window cannot be used until this one closes
        self.title_entry.focus_set()

    def save(self):
        """Validates the fields, then adds or edits the book in the database."""
        # Permission check before touching the database
        if not user_is_allowed(self.controller, "manage_books"):
            return

        # 1. Read and clean what the user typed
        title = self.title_entry.get().strip()
        author = self.author_entry.get().strip()
        genre = self.genre_box.get()
        quantity = to_whole_number(self.quantity_entry.get().strip(), 0, MAX_BOOK_QUANTITY)

        # 2. Check it (the database checks again, this gives immediate feedback)
        if title == "" or len(title) > 100:
            messagebox.showerror("Invalid title", get_status_message(Status.INVALID_TITLE), parent=self)
            return
        if len(author) > 50:
            messagebox.showerror("Invalid author", get_status_message(Status.INVALID_AUTHOR_NAME), parent=self)
            return
        if genre not in GENRES:
            messagebox.showerror("Invalid genre", get_status_message(Status.INVALID_GENRE), parent=self)
            return
        if quantity is None:
            messagebox.showerror("Invalid quantity", get_status_message(Status.INVALID_BOOK_QUANTITY), parent=self)
            return

        # 3. Save. An empty author is stored as "no author" (None / empty)
        if self.book is None:
            status = database.new_book(title, author if author else None, genre, quantity)
        else:
            status = database.edit_book(self.book["id"], title=title, author=author,
                                        genre=genre, quantity=quantity)

        # 4. Tell the user what happened
        if status != Status.SUCCESS:
            messagebox.showerror("Could not save", get_status_message(status), parent=self)
            return

        messagebox.showinfo("Saved", "The book was saved.", parent=self)
        if self.on_saved is not None:
            self.on_saved()
        self.destroy()
