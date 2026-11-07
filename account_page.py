import tkinter as tk
from tkinter import messagebox
import database
from authentification import check_password
from helpers import create_secure_password, verify_secure_password, get_status_message
from gui_helpers import make_button, run_in_background
from status_codes import Status
from theme import *


class AccountPage(tk.Frame):
    """My Account page. A new instance is created every time the user clicks "My Account" in the menu,
    so data loaded in __init__ is always fresh. Everybody (Member, Librarian, Admin) can use it."""

    def __init__(self, parent, controller):
        super().__init__(parent, bg=APP_BG)
        self.controller = controller
        # Logged-in user (a dict): self.controller.current_user["id"], ["username"], ["role"]

        # Fresh information from the database (it also contains available_loans)
        self.user = database.get_user(self.controller.current_user["id"])
        if isinstance(self.user, Status):
            tk.Label(self, text=get_status_message(self.user), font=FONT, fg=ERROR_COLOR, bg=APP_BG).pack(pady=30)
            return

        tk.Label(self, text="My Account", font=FONT_TITLE, fg=CARD_COLOR, bg=APP_BG
                 ).pack(anchor="w", padx=20, pady=(15, 5))
        self.build_information_card()
        self.build_edit_card()

    def build_information_card(self):
        """Read-only information about the account (grid layout inside the card)."""
        card = tk.Frame(self, bg=PANEL_BG, padx=20, pady=12)
        card.pack(anchor="w", padx=20, pady=5)

        rows = [
            ("Username", self.user["username"]),
            ("Role", self.user["role"]),
            ("Member since", self.user["join_date"]),
        ]
        if self.user["role"] == "Member":  # only Members borrow books
            active_loans = 3 - self.user["available_loans"]
            rows.append(("Active loans", f"{active_loans} (you can borrow {self.user['available_loans']} more)"))

        for row_number, (label, value) in enumerate(rows):
            tk.Label(card, text=label, font=FONT_BOLD, bg=PANEL_BG, fg=DARK_TEXT
                     ).grid(row=row_number, column=0, sticky="w", padx=(0, 20), pady=2)
            tk.Label(card, text=str(value), font=FONT, bg=PANEL_BG, fg=DARK_TEXT
                     ).grid(row=row_number, column=1, sticky="w", pady=2)

    def build_edit_card(self):
        """Form to change the username / password, and the button to delete the account."""
        tk.Label(self, text="Edit my account", font=FONT_BOLD, fg=CARD_COLOR, bg=APP_BG
                 ).pack(anchor="w", padx=20, pady=(15, 2))

        card = tk.Frame(self, bg=APP_BG)
        card.pack(anchor="w", padx=20)

        self.username_entry = self.add_field(card, 0, "Username", show=None)
        self.username_entry.insert(0, self.user["username"])
        self.new_password_entry = self.add_field(card, 1, "New password (optional)", show="•")
        self.confirm_entry = self.add_field(card, 2, "Confirm new password", show="•")
        self.current_password_entry = self.add_field(card, 3, "Current password *", show="•")

        self.message_label = tk.Label(card, text="Your current password is needed to save changes or to delete the account.",
                                      font=FONT_SMALL, fg=DARK_TEXT, bg=APP_BG)
        self.message_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))

        buttons = tk.Frame(card, bg=APP_BG)
        buttons.grid(row=5, column=0, columnspan=2, sticky="w", pady=10)
        self.save_button = make_button(buttons, "Save Changes", self.save_changes)
        self.save_button.pack(side="left", padx=(0, 8))
        self.delete_button = make_button(buttons, "Delete My Account", self.delete_account)
        self.delete_button.pack(side="left")

    def add_field(self, card, row, label, show):
        """Adds a label + entry to the form (grid). Returns the entry. show="•" hides the typing."""
        tk.Label(card, text=label, font=FONT, bg=APP_BG, fg=DARK_TEXT
                 ).grid(row=row, column=0, sticky="w", padx=(0, 15), pady=4)
        entry = tk.Entry(card, width=30, font=FONT, show=show)
        entry.grid(row=row, column=1, pady=4, ipady=3)
        return entry

    def set_busy(self, busy, message=""):
        """Disables/enables the buttons while the password is being checked."""
        state = "disabled" if busy else "normal"
        self.save_button.config(state=state)
        self.delete_button.config(state=state)
        self.message_label.config(text=message, fg=DARK_TEXT)

    # ---------------------------------------------------------------- save changes

    def save_changes(self):
        """Validates the form, then checks the current password in a background thread."""
        new_username = self.username_entry.get().strip()
        new_password = self.new_password_entry.get()
        confirm = self.confirm_entry.get()
        current_password = self.current_password_entry.get()

        username_changed = new_username != self.user["username"]
        password_changed = new_password != "" or confirm != ""
        if not username_changed and not password_changed:
            messagebox.showinfo("Nothing to save", "You did not change anything.")
            return
        if username_changed and (len(new_username) < 3 or len(new_username) > 50):
            messagebox.showerror("Invalid username", get_status_message(Status.INVALID_USERNAME))
            return
        if password_changed:
            if new_password != confirm:
                messagebox.showerror("Passwords", "The new passwords do not match.")
                return
            problem = check_password(new_password)
            if problem:
                messagebox.showerror("Invalid password", problem)
                return
        if current_password == "":
            messagebox.showerror("Current password", "Please type your current password.")
            return

        stored_hash = database.get_password_hash(self.user["username"])

        def check_and_hash():
            # Runs in the background thread: no Tkinter and no database here!
            if stored_hash is None or not verify_secure_password(current_password, stored_hash):
                return None                      # None = the current password is wrong
            if password_changed:
                return create_secure_password(new_password)
            return ""                            # "" = password is right, nothing new to hash

        self.set_busy(True, "Saving...")
        run_in_background(self, check_and_hash,
                          lambda result, error: self.finish_save(result, error, new_username if username_changed else None))

    def finish_save(self, result, error, new_username):
        """Called when the background work is finished. Writes the changes to the database."""
        self.set_busy(False)
        if error is not None:
            messagebox.showerror("Error", "Something went wrong. Please try again.")
            return
        if result is None:
            messagebox.showerror("Wrong password", "The current password is not correct.")
            return

        new_hash = result if result != "" else None
        status = database.edit_user(self.user["id"], username=new_username, password_hash=new_hash)
        if status != Status.SUCCESS:
            messagebox.showerror("Could not save", get_status_message(status))
            return

        messagebox.showinfo("Saved", "Your account was updated.")
        if new_username is not None:
            self.controller.current_user["username"] = new_username
            self.controller.dashboard.refresh_user_label()
        self.controller.dashboard.show_section("My Account")  # reload the page with the new data

    # ---------------------------------------------------------------- delete account

    def delete_account(self):
        """Asks for confirmation and the current password, then deletes the account."""
        if self.user["role"] == "Admin":
            messagebox.showinfo("Not possible", "Admin accounts cannot be deleted.")
            return
        current_password = self.current_password_entry.get()
        if current_password == "":
            messagebox.showerror("Current password", "Please type your current password to delete your account.")
            return

        sure = messagebox.askyesno("Delete my account",
                                   "Delete your account for good?\nBooks you still have will be returned "
                                   "and your loan history will be deleted.")
        if not sure:
            return

        stored_hash = database.get_password_hash(self.user["username"])
        self.set_busy(True, "Checking password...")
        run_in_background(self, lambda: stored_hash is not None and verify_secure_password(current_password, stored_hash),
                          self.finish_delete)

    def finish_delete(self, password_ok, error):
        """Called when the password check is finished. Deletes the account if it was correct."""
        self.set_busy(False)
        if error is not None or not password_ok:
            messagebox.showerror("Wrong password", "The current password is not correct.")
            return

        status = database.delete_user(self.user["id"])
        if status != Status.SUCCESS:
            messagebox.showerror("Could not delete", get_status_message(status))
            return

        messagebox.showinfo("Account deleted", "Your account was deleted.")
        self.controller.logout()
