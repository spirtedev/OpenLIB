import tkinter as tk
from tkinter import messagebox
import database
from helpers import get_status_message
from gui_helpers import make_button, make_table, clear_table, selected_id, user_is_allowed
from status_codes import Status
from theme import *


class MembersPage(tk.Frame):
    """Members page (Librarians and Admins): list of all Members with a search box.
    A new instance is created every time the user clicks "Members" in the menu,
    so data loaded in __init__ is always fresh."""

    def __init__(self, parent, controller):
        super().__init__(parent, bg=APP_BG)
        self.controller = controller
        # Logged-in user (a dict): self.controller.current_user["id"], ["username"], ["role"]

        tk.Label(self, text="Members", font=FONT_TITLE, fg=CARD_COLOR, bg=APP_BG
                 ).pack(anchor="w", padx=20, pady=(15, 5))

        # Search bar
        bar = tk.Frame(self, bg=PANEL_BG, padx=10, pady=8)
        bar.pack(fill="x", padx=20, pady=5)
        tk.Label(bar, text="Username", font=FONT_SMALL, bg=PANEL_BG, fg=DARK_TEXT).grid(row=0, column=0, sticky="w")
        self.search_entry = tk.Entry(bar, width=28, font=FONT)
        self.search_entry.grid(row=1, column=0, ipady=3)
        self.search_entry.bind("<Return>", lambda event: self.load_members())
        make_button(bar, "Search", self.load_members).grid(row=1, column=1, padx=(15, 0))
        make_button(bar, "Reset", self.reset_search).grid(row=1, column=2, padx=(8, 0))

        # Table of members
        table_frame, self.table = make_table(self, [
            ("ID", 60), ("Username", 250), ("Member Since", 120), ("Active Loans", 100),
        ])
        table_frame.pack(fill="both", expand=True, padx=20, pady=5)
        self.table.bind("<Double-1>", lambda event: self.view_member_loans())

        self.count_label = tk.Label(self, text="", font=FONT_SMALL, fg=DARK_TEXT, bg=APP_BG)
        self.count_label.pack(anchor="w", padx=20)

        make_button(self, "View Member's Loans", self.view_member_loans).pack(anchor="w", padx=20, pady=(5, 12))

        self.load_members()

    def reset_search(self):
        """Empties the search box and shows all members again."""
        self.search_entry.delete(0, tk.END)
        self.load_members()

    def load_members(self):
        """Searches the Members and fills the table."""
        if not user_is_allowed(self.controller, "view_members"):
            return

        text = self.search_entry.get().strip()
        role = self.controller.current_user["role"]
        # role="Member": show only Members (an Admin would otherwise also get Librarians/Admins)
        members = database.search_users(role, username=text if text else None, role="Member")
        if isinstance(members, Status):
            messagebox.showerror("Error", get_status_message(members))
            return

        clear_table(self.table)
        for member in members:
            details = database.get_user(member["id"])  # has the number of loans left
            active_loans = 3 - details["available_loans"] if not isinstance(details, Status) else "?"
            self.table.insert("", "end", iid=str(member["id"]),
                              values=(member["id"], member["username"], member["join_date"], active_loans))
        self.count_label.config(text=f"{len(members)} member(s) found")

    def view_member_loans(self):
        """Opens the Member Loans page showing only the selected member's loans."""
        if not user_is_allowed(self.controller, "view_member_loans"):
            return
        member_id = selected_id(self.table, "member")
        if member_id is None:
            return
        username = str(self.table.item(str(member_id), "values")[1])
        self.controller.dashboard.show_section("Member Loans", member={"id": member_id, "username": username})
