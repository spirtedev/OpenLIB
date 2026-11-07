import tkinter as tk
from tkinter import ttk, messagebox
import database
from helpers import get_status_message, loan_status
from gui_helpers import make_button, make_table, clear_table, selected_id, user_is_allowed
from status_codes import Status
from theme import *

# Columns shared by both tables: (heading, width)
LOAN_COLUMNS = [("Title", 250), ("Author", 150), ("Loan Date", 90), ("Due Date", 90),
                ("Returned", 90), ("Status", 80)]


class MyLoansPage(tk.Frame):
    """My Loans page (Members only): a tab with the active loans and a tab with the history.
    A new instance is created every time the user clicks "My Loans" in the menu,
    so data loaded in __init__ is always fresh."""

    def __init__(self, parent, controller):
        super().__init__(parent, bg=APP_BG)
        self.controller = controller
        # Logged-in user (a dict): self.controller.current_user["id"], ["username"], ["role"]
        self.user_id = self.controller.current_user["id"]

        tk.Label(self, text="My Loans", font=FONT_TITLE, fg=CARD_COLOR, bg=APP_BG
                 ).pack(anchor="w", padx=20, pady=(15, 2))
        self.info_label = tk.Label(self, text="", font=FONT, fg=DARK_TEXT, bg=APP_BG)
        self.info_label.pack(anchor="w", padx=20)

        # Two tabs
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=20, pady=10)
        active_tab = tk.Frame(notebook, bg=APP_BG)
        history_tab = tk.Frame(notebook, bg=APP_BG)
        notebook.add(active_tab, text="Active Loans")
        notebook.add(history_tab, text="Loan History")

        # Active tab: table + Return button
        active_frame, self.active_table = make_table(active_tab, LOAN_COLUMNS)
        active_frame.pack(fill="both", expand=True, pady=(8, 5))
        make_button(active_tab, "Return Selected Book", self.return_selected_book).pack(anchor="w", pady=(0, 8))

        # History tab: table with every loan, returned or not
        history_frame, self.history_table = make_table(history_tab, LOAN_COLUMNS)
        history_frame.pack(fill="both", expand=True, pady=8)

        self.load_loans()

    def load_loans(self):
        """Reads the member's loans from the database and fills both tables."""
        loans = database.search_loans(user_id=self.user_id)  # ALL his loans, newest first
        if isinstance(loans, Status):
            messagebox.showerror("Error", get_status_message(loans))
            return

        clear_table(self.active_table)
        clear_table(self.history_table)
        for loan in loans:
            status = loan_status(loan)  # "Active", "Overdue" or "Returned"
            tags = ("overdue",) if status == "Overdue" else ()
            values = (loan["title"], loan["author"] or "Unknown", loan["loan_date"],
                      loan["due_date"], loan["returned_at"] or "-", status)

            self.history_table.insert("", "end", iid=str(loan["id"]), values=values, tags=tags)
            if loan["returned_at"] is None:
                self.active_table.insert("", "end", iid=str(loan["id"]), values=values, tags=tags)

        self.update_info_label()

    def update_info_label(self):
        """Shows how many more books the member may borrow."""
        user = database.get_user(self.user_id)
        if isinstance(user, Status):
            return
        self.info_label.config(text=f"You can borrow {user['available_loans']} more book(s) (maximum 3 at a time).")

    def return_selected_book(self):
        """Returns the selected active loan (after checking that it is really his loan)."""
        if not user_is_allowed(self.controller, "view_my_loans"):
            return
        loan_id = selected_id(self.active_table, "loan")
        if loan_id is None:
            return

        # Safety check: the loan must belong to the logged-in member and still be active
        own_loan = database.search_loans(id=loan_id, user_id=self.user_id, active_loans_only=True)
        if isinstance(own_loan, Status) or not own_loan:
            messagebox.showerror("Error", get_status_message(Status.LOAN_NOT_FOUND))
            self.load_loans()
            return

        if not messagebox.askyesno("Return book", f'Return "{own_loan[0]["title"]}" now?'):
            return

        status = database.return_book(loan_id)
        if status == Status.SUCCESS:
            messagebox.showinfo("Returned", "Thank you! The book was returned.")
        else:
            messagebox.showerror("Could not return", get_status_message(status))
        self.load_loans()
