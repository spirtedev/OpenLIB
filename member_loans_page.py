import tkinter as tk
from tkinter import ttk, messagebox
import database
from helpers import get_status_message, loan_status
from gui_helpers import make_button, make_table, clear_table, user_is_allowed
from status_codes import Status
from theme import *

# Choices of the status drop-down
ALL_LOANS = "All loans"
STATUS_CHOICES = [ALL_LOANS, "Active", "Overdue", "Returned"]


class MemberLoansPage(tk.Frame):
    """Member Loans page (Librarians and Admins): every member's loans, with filters.
    Optional parameter `member`: a dict with "id" and "username". When it is given, only that
    member's loans are shown (used by the "View Loans" buttons of the Members/Users pages).
    A new instance is created every time the page is opened, so data is always fresh."""

    def __init__(self, parent, controller, member=None):
        super().__init__(parent, bg=APP_BG)
        self.controller = controller
        # Logged-in user (a dict): self.controller.current_user["id"], ["username"], ["role"]
        self.member = member

        tk.Label(self, text="Member Loans", font=FONT_TITLE, fg=CARD_COLOR, bg=APP_BG
                 ).pack(anchor="w", padx=20, pady=(15, 5))

        self.build_filter_bar()

        table_frame, self.table = make_table(self, [
            ("Loan ID", 60), ("Member", 110), ("Title", 200), ("Author", 120),
            ("Loan Date", 85), ("Due Date", 85), ("Returned", 85), ("Status", 70),
        ])
        table_frame.pack(fill="both", expand=True, padx=20, pady=5)

        self.count_label = tk.Label(self, text="", font=FONT_SMALL, fg=DARK_TEXT, bg=APP_BG)
        self.count_label.pack(anchor="w", padx=20, pady=(0, 10))

        self.load_loans()

    def build_filter_bar(self):
        """Member name box (or the name of the chosen member), status drop-down, buttons."""
        bar = tk.Frame(self, bg=PANEL_BG, padx=10, pady=8)
        bar.pack(fill="x", padx=20, pady=5)

        tk.Label(bar, text="Member", font=FONT_SMALL, bg=PANEL_BG, fg=DARK_TEXT
                 ).grid(row=0, column=0, sticky="w")
        tk.Label(bar, text="Status", font=FONT_SMALL, bg=PANEL_BG, fg=DARK_TEXT
                 ).grid(row=0, column=1, sticky="w", padx=(10, 0))

        if self.member is None:
            self.username_entry = tk.Entry(bar, width=24, font=FONT)
            self.username_entry.grid(row=1, column=0, sticky="w", ipady=3)
            self.username_entry.bind("<Return>", lambda event: self.load_loans())
        else:
            # Showing one member only: no search box, just his name
            self.username_entry = None
            tk.Label(bar, text=self.member["username"], font=FONT_BOLD, bg=PANEL_BG, fg=DARK_TEXT
                     ).grid(row=1, column=0, sticky="w")

        self.status_box = ttk.Combobox(bar, values=STATUS_CHOICES, state="readonly", width=12)
        self.status_box.set(ALL_LOANS)
        self.status_box.grid(row=1, column=1, sticky="w", padx=(10, 0))

        make_button(bar, "Search", self.load_loans).grid(row=1, column=2, padx=(15, 0))
        if self.member is None:
            make_button(bar, "Reset", self.reset_filters).grid(row=1, column=3, padx=(8, 0))
        else:
            make_button(bar, "All members' loans",
                        lambda: self.controller.dashboard.show_section("Member Loans")
                        ).grid(row=1, column=3, padx=(8, 0))

    def reset_filters(self):
        """Empties the filters and shows all loans."""
        if self.username_entry is not None:
            self.username_entry.delete(0, tk.END)
        self.status_box.set(ALL_LOANS)
        self.load_loans()

    def load_loans(self):
        """Reads the filters, searches the loans and fills the table."""
        if not user_is_allowed(self.controller, "view_member_loans"):
            return

        status_filter = self.status_box.get()
        search = {}  # keyword arguments for database.search_loans
        if self.member is not None:
            search["user_id"] = self.member["id"]
        elif self.username_entry.get().strip() != "":
            search["username"] = self.username_entry.get().strip()
        if status_filter == "Active":
            search["active_loans_only"] = True
        elif status_filter == "Overdue":
            search["overdue_only"] = True

        loans = database.search_loans(**search)
        if isinstance(loans, Status):
            messagebox.showerror("Error", get_status_message(loans))
            return
        if status_filter == "Returned":
            loans = [loan for loan in loans if loan["returned_at"] is not None]

        clear_table(self.table)
        for loan in loans:
            status = loan_status(loan)
            tags = ("overdue",) if status == "Overdue" else ()
            self.table.insert("", "end", iid=str(loan["id"]), tags=tags, values=(
                loan["id"], loan["username"], loan["title"], loan["author"] or "Unknown",
                loan["loan_date"], loan["due_date"], loan["returned_at"] or "-", status))
        self.count_label.config(text=f"{len(loans)} loan(s) found")
