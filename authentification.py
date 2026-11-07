import tkinter as tk
from tkinter import messagebox
import database
from helpers import create_secure_password, verify_secure_password, get_status_message
from gui_helpers import load_image, run_in_background
from theme import *
from status_codes import Status


def check_password(password: str) -> str:
    """Returns an error message if the password fails simple rules, else empty string."""
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not any(c.isupper() for c in password):
        return "Must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return "Must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return "Must contain at least one digit."
    return ""


class LoginPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=AUTH_BG)
        self.controller = controller

        # Centered Box
        card = tk.Frame(self, bg=CARD_COLOR, padx=30, pady=25)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # Logo (kept as self.logo_image so Tkinter does not delete it)
        self.logo_image = load_image("openliblogo.png", 220, 120)
        if self.logo_image:
            tk.Label(card, image=self.logo_image, bg=CARD_COLOR).pack(pady=(0, 15))
        else:
            # Fallback if the image or Pillow is missing
            tk.Label(card, text="OpenLIB Login", font=FONT_TITLE, fg=GOLD_COLOR, bg=CARD_COLOR).pack(pady=(0, 15))

        # Username Input
        tk.Label(card, text="Username", fg=TEXT_COLOR, bg=CARD_COLOR, font=FONT).pack(anchor="w")
        self.user_ent = tk.Entry(card, width=28, font=FONT)
        self.user_ent.pack(pady=(2, 10), ipady=3)

        # Password Input
        tk.Label(card, text="Password", fg=TEXT_COLOR, bg=CARD_COLOR, font=FONT).pack(anchor="w")
        self.pass_ent = tk.Entry(card, show="•", width=28, font=FONT)
        self.pass_ent.pack(pady=(2, 6), ipady=3)
        self.pass_ent.bind("<Return>", lambda e: self.login())  # Enter key = Sign In

        # Error text
        self.err_lbl = tk.Label(card, text="", fg=ERROR_COLOR, bg=CARD_COLOR, font=FONT_SMALL)
        self.err_lbl.pack(pady=4)

        # Submit Button (kept in self.login_button so it can be disabled while signing in)
        self.login_button = tk.Button(card, text="Sign In", bg=GOLD_COLOR, fg=DARK_TEXT, font=FONT_BOLD,
                                      relief="flat", cursor="hand2", command=self.login)
        self.login_button.pack(fill="x", pady=6, ipady=3)

        # Switch to Register Link
        link = tk.Label(card, text="Don't have an account? Register", fg=MUTED_COLOR, bg=CARD_COLOR,
                        cursor="hand2", font=(*FONT_SMALL, "underline"))
        link.pack(pady=(6, 0))
        link.bind("<Button-1>", lambda e: controller.show_frame("RegisterPage"))

    def login(self):
        """Checks the fields, then checks the password in a background thread."""
        u = self.user_ent.get().strip()
        p = self.pass_ent.get()  # password is NOT stripped: spaces can be part of it
        if not u or not p:
            self.err_lbl.config(text="Please fill in both fields.")
            return

        # Get the stored password hash of this username (None = unknown username)
        stored_hash = database.get_password_hash(u)
        if stored_hash is None:
            self.err_lbl.config(text=get_status_message(Status.UNAUTHORIZED))
            return

        # Checking the password takes a moment (on purpose, it is hashed 600,000 times).
        # It runs in a background thread so the window stays responsive.
        self.err_lbl.config(text="Signing in...")
        self.login_button.config(state="disabled")
        run_in_background(
            self,
            lambda: verify_secure_password(p, stored_hash),
            lambda password_ok, error: self.finish_login(u, password_ok, error),
        )

    def finish_login(self, username, password_ok, error):
        """Called when the password check is finished. Opens the dashboard if it was correct."""
        self.login_button.config(state="normal")
        if error is not None or not password_ok:
            self.err_lbl.config(text=get_status_message(Status.UNAUTHORIZED))
            return

        user = database.get_user_by_username(username)
        if isinstance(user, Status):  # the account was deleted in the meantime
            self.err_lbl.config(text=get_status_message(Status.UNAUTHORIZED))
            return

        self.controller.current_user = dict(user)
        self.controller.show_frame("DashboardPage")

    def on_show(self):
        self.user_ent.delete(0, tk.END)
        self.pass_ent.delete(0, tk.END)
        self.err_lbl.config(text="")


class RegisterPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=AUTH_BG)
        self.controller = controller

        # Centered Box
        card = tk.Frame(self, bg=CARD_COLOR, padx=30, pady=25)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # Logo (kept as self.logo_image so Tkinter does not delete it)
        self.logo_image = load_image("openliblogo.png", 220, 120)
        if self.logo_image:
            tk.Label(card, image=self.logo_image, bg=CARD_COLOR).pack(pady=(0, 15))
        else:
            # Fallback if the image or Pillow is missing
            tk.Label(card, text="Join OpenLIB", font=FONT_TITLE, fg=GOLD_COLOR, bg=CARD_COLOR).pack(pady=(0, 15))

        # Fields
        tk.Label(card, text="Username", fg=TEXT_COLOR, bg=CARD_COLOR, font=FONT).pack(anchor="w")
        self.user_ent = tk.Entry(card, width=28, font=FONT)
        self.user_ent.pack(pady=(2, 8), ipady=3)

        tk.Label(card, text="Password", fg=TEXT_COLOR, bg=CARD_COLOR, font=FONT).pack(anchor="w")
        self.pass_ent = tk.Entry(card, show="•", width=28, font=FONT)
        self.pass_ent.pack(pady=(2, 8), ipady=3)

        tk.Label(card, text="Confirm Password", fg=TEXT_COLOR, bg=CARD_COLOR, font=FONT).pack(anchor="w")
        self.conf_ent = tk.Entry(card, show="•", width=28, font=FONT)
        self.conf_ent.pack(pady=(2, 6), ipady=3)
        self.conf_ent.bind("<Return>", lambda e: self.register())  # Enter key = Register

        # Error text
        self.err_lbl = tk.Label(card, text="", fg=ERROR_COLOR, bg=CARD_COLOR, font=FONT_SMALL)
        self.err_lbl.pack(pady=4)

        # Submit Button (kept in self.register_button so it can be disabled while hashing)
        self.register_button = tk.Button(card, text="Register", bg=GOLD_COLOR, fg=DARK_TEXT, font=FONT_BOLD,
                                         relief="flat", cursor="hand2", command=self.register)
        self.register_button.pack(fill="x", pady=6, ipady=3)

        # Switch to Login Link
        link = tk.Label(card, text="Already have an account? Sign in", fg=MUTED_COLOR, bg=CARD_COLOR,
                        cursor="hand2", font=(*FONT_SMALL, "underline"))
        link.pack(pady=(6, 0))
        link.bind("<Button-1>", lambda e: controller.show_frame("LoginPage"))

    def register(self):
        u = self.user_ent.get().strip()
        p = self.pass_ent.get()
        c = self.conf_ent.get()

        if not u or not p or not c:
            self.err_lbl.config(text="All fields are required.")
            return
        if len(u) < 3 or len(u) > 50:
            self.err_lbl.config(text="Username must be between 3 and 50 characters.")
            return
        if p != c:
            self.err_lbl.config(text="Passwords do not match.")
            return

        pass_err = check_password(p)
        if pass_err:
            self.err_lbl.config(text=pass_err)
            return

        # Hashing takes a moment, so it runs in a background thread
        self.err_lbl.config(text="Creating account...")
        self.register_button.config(state="disabled")
        run_in_background(
            self,
            lambda: create_secure_password(p),
            lambda hashed, error: self.finish_register(u, hashed, error),
        )

    def finish_register(self, username, hashed, error):
        """
        Called when the password has been hashed. Saves the new account.
        The ROLE is decided by the database (first account ever = Admin, others = Member).
        """
        self.register_button.config(state="normal")
        if error is not None:
            self.err_lbl.config(text="Could not create the account. Please try again.")
            return

        status = database.register_user(username, hashed)

        if status == Status.SUCCESS:
            message = "Account created! You can now sign in."
            new_user = database.get_user_by_username(username)
            if not isinstance(new_user, Status) and new_user["role"] == "Admin":
                message = "Account created! As the first user, you are the Admin."
            messagebox.showinfo("Success", message)
            self.controller.show_frame("LoginPage")
        else:
            # Translates USERNAME_ALREADY_EXISTS, INVALID_USERNAME, DATABASE_ERROR...
            self.err_lbl.config(text=get_status_message(status))

    def on_show(self):
        self.user_ent.delete(0, tk.END)
        self.pass_ent.delete(0, tk.END)
        self.conf_ent.delete(0, tk.END)
        self.err_lbl.config(text="")
