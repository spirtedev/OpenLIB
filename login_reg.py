import os
import tkinter as tk
from tkinter import messagebox
import database
from helpers import create_secure_password
from status_codes import Status

# Colors & Fonts
BG_COLOR = "#0F172A"      
CARD_COLOR = "#1E293B"    
TEXT_COLOR = "#F8FAFC"    
GOLD_COLOR = "#EAB308"    
ERROR_COLOR = "#F87171"  
FONT = ("Segoe UI", 10)


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
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller

        # Centered Box
        card = tk.Frame(self, bg=CARD_COLOR, padx=30, pady=25)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        tk.Label(card, text="OpenLIB Login", font=("Segoe UI", 16, "bold"), fg=GOLD_COLOR, bg=CARD_COLOR).pack(pady=(0, 15))

        # Username Input
        tk.Label(card, text="Username", fg=TEXT_COLOR, bg=CARD_COLOR, font=FONT).pack(anchor="w")
        self.user_ent = tk.Entry(card, width=28, font=FONT)
        self.user_ent.pack(pady=(2, 10), ipady=3)

        # Password Input
        tk.Label(card, text="Password", fg=TEXT_COLOR, bg=CARD_COLOR, font=FONT).pack(anchor="w")
        self.pass_ent = tk.Entry(card, show="•", width=28, font=FONT)
        self.pass_ent.pack(pady=(2, 6), ipady=3)

        # Error text
        self.err_lbl = tk.Label(card, text="", fg=ERROR_COLOR, bg=CARD_COLOR, font=("Segoe UI", 9))
        self.err_lbl.pack(pady=4)

        # Submit Button
        tk.Button(card, text="Sign In", bg=GOLD_COLOR, fg=BG_COLOR, font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2", command=self.login).pack(fill="x", pady=6, ipady=3)

        # Switch to Register Link
        link = tk.Label(card, text="Don't have an account? Register", fg="#94A3B8", bg=CARD_COLOR,
                        cursor="hand2", font=("Segoe UI", 9, "underline"))
        link.pack(pady=(6, 0))
        link.bind("<Button-1>", lambda e: controller.show_frame("RegisterPage"))

    def login(self):
        u, p = self.user_ent.get().strip(), self.pass_ent.get().strip()
        if not u or not p:
            self.err_lbl.config(text="Please fill in both fields.")
            return

        result = database.login_user(u, p)
        if result == Status.UNAUTHORIZED:
            self.err_lbl.config(text="Invalid username or password.")
            return

        self.controller.current_user = dict(result)
        messagebox.showinfo("Success", f"Welcome back, {u}!")

    def on_show(self):
        self.user_ent.delete(0, tk.END)
        self.pass_ent.delete(0, tk.END)
        self.err_lbl.config(text="")


class RegisterPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller

        # Centered Box
        card = tk.Frame(self, bg=CARD_COLOR, padx=30, pady=25)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        tk.Label(card, text="Join OpenLIB", font=("Segoe UI", 16, "bold"), fg=GOLD_COLOR, bg=CARD_COLOR).pack(pady=(0, 15))

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

        # Error text
        self.err_lbl = tk.Label(card, text="", fg=ERROR_COLOR, bg=CARD_COLOR, font=("Segoe UI", 9))
        self.err_lbl.pack(pady=4)

        # Submit Button
        tk.Button(card, text="Register", bg=GOLD_COLOR, fg=BG_COLOR, font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2", command=self.register).pack(fill="x", pady=6, ipady=3)

        # Switch to Login Link
        link = tk.Label(card, text="Already have an account? Sign in", fg="#94A3B8", bg=CARD_COLOR,
                        cursor="hand2", font=("Segoe UI", 9, "underline"))
        link.pack(pady=(6, 0))
        link.bind("<Button-1>", lambda e: controller.show_frame("LoginPage"))

    def register(self):
        u = self.user_ent.get().strip()
        p = self.pass_ent.get().strip()
        c = self.conf_ent.get().strip()

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

        # Hash and insert into database
        hashed = create_secure_password(p)
        status = database.new_user(username=u, password_hash=hashed, role="Member")

        if status == Status.SUCCESS:
            messagebox.showinfo("Success", "Account created! You can now sign in.")
            self.controller.show_frame("LoginPage")
        elif status == Status.USERNAME_ALREADY_EXISTS:
            self.err_lbl.config(text="This username is already taken.")
        else:
            self.err_lbl.config(text="Database error occurred.")

    def on_show(self):
        self.user_ent.delete(0, tk.END)
        self.pass_ent.delete(0, tk.END)
        self.conf_ent.delete(0, tk.END)
        self.err_lbl.config(text="")
