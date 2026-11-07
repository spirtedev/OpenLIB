import tkinter as tk
from tkinter import ttk, messagebox
import database
from helpers import get_status_message
from gui_helpers import make_button, make_table, clear_table, selected_id, user_is_allowed
from status_codes import Status
from theme import *
from user_form import UserForm, ROLES

ALL_ROLES = "All roles"


class UsersPage(tk.Frame):
    """Users page (Admins only): every account, with create / edit / delete.
    A new instance is created every time the user clicks "Users" in the menu,
    so data loaded in __init__ is always fresh."""

    def __init__(self, parent, controller):
        super().__init__(parent, bg=APP_BG)
        self.controller = controller
        # Logged-in user (a dict): self.controller.current_user["id"], ["username"], ["role"]

        tk.Label(self, text="Users", font=FONT_TITLE, fg=CARD_COLOR, bg=APP_BG
                 ).pack(anchor="w", padx=20, pady=(15, 5))

        self.build_filter_bar()

        table_frame, self.table = make_table(self, [
            ("ID", 60), ("Username", 230), ("Role", 100), ("Member Since", 110), ("Active Loans", 90),
        ])
        table_frame.pack(fill="both", expand=True, padx=20, pady=5)

        self.count_label = tk.Label(self, text="", font=FONT_SMALL, fg=DARK_TEXT, bg=APP_BG)
        self.count_label.pack(anchor="w", padx=20)

        buttons = tk.Frame(self, bg=APP_BG)
        buttons.pack(fill="x", padx=20, pady=(5, 12))
        make_button(buttons, "Add User", self.add_user).pack(side="left", padx=(0, 8))
        make_button(buttons, "Edit User", self.edit_user).pack(side="left", padx=(0, 8))
        make_button(buttons, "Delete User", self.delete_user).pack(side="left", padx=(0, 8))
        make_button(buttons, "View User's Loans", self.view_user_loans).pack(side="left", padx=(0, 8))

        self.load_users()

    def build_filter_bar(self):
        """Username search box, role drop-down and the Search / Reset buttons."""
        bar = tk.Frame(self, bg=PANEL_BG, padx=10, pady=8)
        bar.pack(fill="x", padx=20, pady=5)
        tk.Label(bar, text="Username", font=FONT_SMALL, bg=PANEL_BG, fg=DARK_TEXT).grid(row=0, column=0, sticky="w")
        tk.Label(bar, text="Role", font=FONT_SMALL, bg=PANEL_BG, fg=DARK_TEXT
                 ).grid(row=0, column=1, sticky="w", padx=(10, 0))

        self.search_entry = tk.Entry(bar, width=26, font=FONT)
        self.search_entry.grid(row=1, column=0, ipady=3)
        self.search_entry.bind("<Return>", lambda event: self.load_users())

        self.role_box = ttk.Combobox(bar, values=[ALL_ROLES] + ROLES, state="readonly", width=12)
        self.role_box.set(ALL_ROLES)
        self.role_box.grid(row=1, column=1, padx=(10, 0))

        make_button(bar, "Search", self.load_users).grid(row=1, column=2, padx=(15, 0))
        make_button(bar, "Reset", self.reset_filters).grid(row=1, column=3, padx=(8, 0))

    def reset_filters(self):
        """Empties the filters and shows all users again."""
        self.search_entry.delete(0, tk.END)
        self.role_box.set(ALL_ROLES)
        self.load_users()

    def load_users(self):
        """Searches the users with the filters and fills the table."""
        if not user_is_allowed(self.controller, "manage_users"):
            return

        text = self.search_entry.get().strip()
        role = self.role_box.get()
        users = database.search_users(
            self.controller.current_user["role"],
            username=text if text else None,
            role=None if role == ALL_ROLES else role,
        )
        if isinstance(users, Status):
            messagebox.showerror("Error", get_status_message(users))
            return

        clear_table(self.table)
        for user in users:
            details = database.get_user(user["id"])  # has the number of loans left
            active_loans = "-"
            if not isinstance(details, Status) and details["role"] == "Member":
                active_loans = 3 - details["available_loans"]
            self.table.insert("", "end", iid=str(user["id"]),
                              values=(user["id"], user["username"], user["role"], user["join_date"], active_loans))
        self.count_label.config(text=f"{len(users)} user(s) found")

    def selected_user(self):
        """Returns the selected user as (id, username, role), or None if nothing is selected."""
        user_id = selected_id(self.table, "user")
        if user_id is None:
            return None
        values = self.table.item(str(user_id), "values")
        return user_id, str(values[1]), values[2]

    def add_user(self):
        """Opens the empty 'Add User' form."""
        if not user_is_allowed(self.controller, "manage_users"):
            return
        UserForm(self, self.controller, user=None, on_saved=self.after_change)

    def edit_user(self):
        """Opens the 'Edit User' form for the selected user."""
        if not user_is_allowed(self.controller, "manage_users"):
            return
        selected = self.selected_user()
        if selected is None:
            return
        user = database.get_user(selected[0])
        if isinstance(user, Status):
            messagebox.showerror("Error", get_status_message(user))
            self.load_users()
            return
        UserForm(self, self.controller, user=user, on_saved=self.after_change)

    def delete_user(self):
        """Deletes the selected user after asking for confirmation."""
        if not user_is_allowed(self.controller, "manage_users"):
            return
        selected = self.selected_user()
        if selected is None:
            return
        user_id, username, role = selected

        sure = messagebox.askyesno("Delete user",
                                   f'Delete the account "{username}"?\n'
                                   "Any books he still has will be returned and his loan history will be deleted.")
        if not sure:
            return

        status = database.delete_user(user_id)
        if status == Status.SUCCESS:
            messagebox.showinfo("Deleted", "The account was deleted.")
        else:
            messagebox.showerror("Could not delete", get_status_message(status))
        self.after_change()

    def view_user_loans(self):
        """Opens the Member Loans page showing only the selected user's loans."""
        if not user_is_allowed(self.controller, "view_member_loans"):
            return
        selected = self.selected_user()
        if selected is None:
            return
        self.controller.dashboard.show_section("Member Loans", member={"id": selected[0], "username": selected[1]})

    def after_change(self):
        """
        Called after a user was added, edited or deleted. Reloads this page through the
        dashboard, which also notices if the Admin changed his OWN role.
        """
        self.controller.dashboard.show_section("Users")
