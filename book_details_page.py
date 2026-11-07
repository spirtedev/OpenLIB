import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox
import database
from helpers import MAX_LOAN_DURATION, get_status_message, to_whole_number
from gui_helpers import make_button, user_is_allowed
from permissions import has_permission
from status_codes import Status
from theme import *

DEFAULT_LOAN_DAYS = 14


class BookDetailsPage(tk.Frame):
    """Details of one book. Members can also borrow it here.
    Opened with: self.controller.dashboard.show_book_details(book_id)"""

    def __init__(self, parent, controller, book_id):
        super().__init__(parent, bg=APP_BG)
        self.controller = controller
        self.book_id = book_id
        self.user = self.controller.current_user  # a dict: id, username, role...

        # "Back" button: returns to the books list
        make_button(self, "< Back to books", lambda: self.controller.dashboard.show_section("Books")
                    ).pack(anchor="w", padx=20, pady=(15, 5))

        found = database.search_books(id=book_id)
        if isinstance(found, Status) or not found:
            tk.Label(self, text="This book no longer exists.", font=FONT, fg=ERROR_COLOR, bg=APP_BG
                     ).pack(padx=20, pady=20)
            return
        self.book = found[0]

        self.build_details()
        self.build_borrow_area()

    def build_details(self):
        """The card with the information about the book (grid layout inside the card)."""
        book = self.book
        tk.Label(self, text=book["title"], font=FONT_TITLE, fg=CARD_COLOR, bg=APP_BG,
                 wraplength=600, justify="left").pack(anchor="w", padx=20, pady=(5, 10))

        card = tk.Frame(self, bg=PANEL_BG, padx=20, pady=15)
        card.pack(anchor="w", padx=20)

        author = book["author"] if book["author"] else "Unknown"
        rows = [
            ("Book ID", book["id"]),
            ("Author", author),
            ("Genre", book["genre"]),
            ("Copies available", book["quantity"]),
        ]
        for row_number, (label, value) in enumerate(rows):
            tk.Label(card, text=label, font=FONT_BOLD, bg=PANEL_BG, fg=DARK_TEXT
                     ).grid(row=row_number, column=0, sticky="w", padx=(0, 20), pady=3)
            tk.Label(card, text=str(value), font=FONT, bg=PANEL_BG, fg=DARK_TEXT
                     ).grid(row=row_number, column=1, sticky="w", pady=3)

    def build_borrow_area(self):
        """The borrow controls. Only Members can borrow books."""
        area = tk.Frame(self, bg=APP_BG)
        area.pack(anchor="w", padx=20, pady=20)

        if not has_permission(self.user["role"], "borrow_books"):
            tk.Label(area, text="Only Member accounts can borrow books.", font=FONT_SMALL,
                     fg=DARK_TEXT, bg=APP_BG).pack(anchor="w")
            return

        if self.book["quantity"] <= 0:
            tk.Label(area, text="No copies are available right now.", font=FONT, fg=ERROR_COLOR,
                     bg=APP_BG).pack(anchor="w")
            return

        # How many days to borrow it (1 to 21)
        tk.Label(area, text=f"Loan duration in days (1-{MAX_LOAN_DURATION}):", font=FONT, fg=DARK_TEXT,
                 bg=APP_BG).pack(side="left")
        self.days_entry = tk.Spinbox(area, from_=1, to=MAX_LOAN_DURATION, width=5, font=FONT)
        self.days_entry.delete(0, tk.END)
        self.days_entry.insert(0, str(DEFAULT_LOAN_DAYS))
        self.days_entry.pack(side="left", padx=8)
        make_button(area, "Borrow this book", self.borrow_book).pack(side="left", padx=8)

    def borrow_book(self):
        """Borrows the book for the logged-in Member."""
        # Permission check before touching the database
        if not user_is_allowed(self.controller, "borrow_books"):
            return

        days = to_whole_number(self.days_entry.get().strip(), 1, MAX_LOAN_DURATION)
        if days is None:
            messagebox.showerror("Invalid duration", get_status_message(Status.INVALID_LOAN_DURATION))
            return

        status = database.loan_book(self.user["id"], self.book_id, days)
        if status != Status.SUCCESS:
            messagebox.showerror("Could not borrow", get_status_message(status))
        else:
            due_date = (date.today() + timedelta(days=days)).isoformat()
            messagebox.showinfo("Book borrowed", f'You borrowed "{self.book["title"]}".\nPlease return it by {due_date}.')

        # Show the page again so the number of copies is up to date
        self.controller.dashboard.show_book_details(self.book_id)
