import tkinter as tk
from tkinter import ttk, messagebox
import database
from authentification import check_password
from helpers import create_secure_password, get_status_message
from gui_helpers import make_button, center_window, run_in_background, user_is_allowed
from status_codes import Status
from theme import *

ROLES = ["Member", "Librarian", "Admin"]


class UserForm(tk.Toplevel):
    """
    A small pop-up window (for Admins) to create a user or to edit an existing one.
    Parameters:
      parent     - the page that opens the form
      controller - the main app
      user       - None to CREATE a user, or a user row (from database.get_user) to EDIT it
      on_saved   - function called after a successful save
    """

    def __init__(self, parent, controller, user=None, on_saved=None):
        super().__init__(parent)
        self.controller = controller
        self.user = user
        self.on_saved = on_saved

        self.title("Add User" if user is None else "Edit User")
        self.configure(bg=APP_BG, padx=20, pady=15)
        self.resizable(False, False)

        # Everything in this window is placed with grid(): column 0 = labels, column 1 = fields
        tk.Label(self, text="Username *", font=FONT, bg=APP_BG, fg=DARK_TEXT).grid(row=0, column=0, sticky="w", pady=6)
        self.username_entry = tk.Entry(self, width=30, font=FONT)
        self.username_entry.grid(row=0, column=1, pady=6, ipady=3)

        password_label = "Password *" if user is None else "New password"
        tk.Label(self, text=password_label, font=FONT, bg=APP_BG, fg=DARK_TEXT).grid(row=1, column=0, sticky="w", pady=6)
        self.password_entry = tk.Entry(self, show="•", width=30, font=FONT)
        self.password_entry.grid(row=1, column=1, pady=6, ipady=3)

        tk.Label(self, text="Confirm password", font=FONT, bg=APP_BG, fg=DARK_TEXT).grid(row=2, column=0, sticky="w", pady=6)
        self.confirm_entry = tk.Entry(self, show="•", width=30, font=FONT)
        self.confirm_entry.grid(row=2, column=1, pady=6, ipady=3)

        tk.Label(self, text="Role *", font=FONT, bg=APP_BG, fg=DARK_TEXT).grid(row=3, column=0, sticky="w", pady=6)
        self.role_box = ttk.Combobox(self, values=ROLES, state="readonly", width=15)
        self.role_box.set("Member")
        self.role_box.grid(row=3, column=1, sticky="w", pady=6)

        if user is not None:
            tk.Label(self, text="Leave the password empty to keep the current one.", font=FONT_SMALL,
                     bg=APP_BG, fg=DARK_TEXT).grid(row=4, column=0, columnspan=2, sticky="w")

        self.message_label = tk.Label(self, text="", font=FONT_SMALL, bg=APP_BG, fg=ERROR_COLOR)
        self.message_label.grid(row=5, column=0, columnspan=2, pady=(6, 0))

        buttons = tk.Frame(self, bg=APP_BG)
        buttons.grid(row=6, column=0, columnspan=2, pady=(10, 0))
        self.save_button = make_button(buttons, "Save", self.save)
        self.save_button.pack(side="left", padx=6)
        make_button(buttons, "Cancel", self.destroy).pack(side="left", padx=6)

        # When editing, fill the fields with the current values
        if user is not None:
            self.username_entry.insert(0, user["username"])
            self.role_box.set(user["role"])

        center_window(self, 500, 340)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.username_entry.focus_set()

    def save(self):
        """Validates the fields. If they are fine, hashes the password (if any) in the background."""
        if not user_is_allowed(self.controller, "manage_users"):
            return

        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        role = self.role_box.get()

        if len(username) < 3 or len(username) > 50:
            self.message_label.config(text=get_status_message(Status.INVALID_USERNAME))
            return
        if role not in ROLES:
            self.message_label.config(text=get_status_message(Status.INVALID_ROLE))
            return

        # A password is required for a new user and optional when editing
        if self.user is None or password != "" or confirm != "":
            if password != confirm:
                self.message_label.config(text="Passwords do not match.")
                return
            problem = check_password(password)
            if problem:
                self.message_label.config(text=problem)
                return

        self.save_button.config(state="disabled")
        self.message_label.config(text="Saving...", fg=DARK_TEXT)

        if password == "":
            # Nothing to hash: continue straight away
            self.finish_save(username, role, None, None)
        else:
            run_in_background(self, lambda: create_secure_password(password),
                              lambda hashed, error: self.finish_save(username, role, hashed, error))

    def finish_save(self, username, role, password_hash, error):
        """Writes the user to the database (the password is already hashed)."""
        self.save_button.config(state="normal")
        self.message_label.config(fg=ERROR_COLOR)
        if error is not None:
            self.message_label.config(text="Could not process the password. Please try again.")
            return

        if self.user is None:
            status = database.new_user(username, password_hash, role)
        else:
            # Only send what really changed
            changes = {}
            if username != self.user["username"]:
                changes["username"] = username
            if role != self.user["role"]:
                changes["role"] = role
            if password_hash is not None:
                changes["password_hash"] = password_hash
            status = database.edit_user(self.user["id"], **changes)

        if status == Status.NOTHING_TO_EDIT:
            self.message_label.config(text="You did not change anything.")
            return
        if status != Status.SUCCESS:
            self.message_label.config(text=get_status_message(status))
            return

        messagebox.showinfo("Saved", "The user was saved.", parent=self)
        if self.on_saved is not None:
            self.on_saved()
        self.destroy()
