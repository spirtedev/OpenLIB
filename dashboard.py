import tkinter as tk
from tkinter import messagebox
import database
from gui_helpers import load_image
from permissions import has_permission
from status_codes import Status
from theme import *
from books_page import BooksPage
from book_details_page import BookDetailsPage
from my_loans_page import MyLoansPage
from account_page import AccountPage
from members_page import MembersPage
from member_loans_page import MemberLoansPage
from users_page import UsersPage


BANNER_WIDTH = 280       # width of the left banner panel in pixels (change it here)
BANNER_TOP_MARGIN = 60   # empty space above the banner, so it lines up with the page titles
BANNER_MAX_HEIGHT = 590  # the banner is never taller than this (window height 650 - top margin)

# Menu name -> page class. To add a page: create its file, import it above, add a line here.
PAGES = {
    "Books": BooksPage,
    "My Loans": MyLoansPage,
    "My Account": AccountPage,
    "Members": MembersPage,
    "Member Loans": MemberLoansPage,
    "Users": UsersPage,
}

# Menu name -> the permission (see permissions.py) needed to open that page
PAGE_PERMISSIONS = {
    "Books": "view_books",
    "My Loans": "view_my_loans",
    "My Account": "manage_own_account",
    "Members": "view_members",
    "Member Loans": "view_member_loans",
    "Users": "manage_users",
}

# Which menu buttons each role sees
NAV_BY_ROLE = {
    "Member": ["Books", "My Loans", "My Account"],
    "Librarian": ["Books", "Members", "Member Loans", "My Account"],
    "Admin": ["Books", "Users", "Member Loans", "My Account"],
}


class DashboardPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=APP_BG)
        self.controller = controller
        self.user_label = None  # the "name (role)" label of the menu bar, created in on_show

        # LEFT SIDE: banner image
        left = tk.Frame(self, bg=CARD_COLOR, width=BANNER_WIDTH)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)  # keep the fixed width

        self.banner_image = load_image("openlibbanner.png", BANNER_WIDTH, BANNER_MAX_HEIGHT)
        if self.banner_image:
            # anchor="n" = at the TOP of the panel (no expand, so it is not centered);
            # pady=(margin, 0) = empty space above the banner, none below
            tk.Label(left, image=self.banner_image, bg=CARD_COLOR
                     ).pack(side="top", anchor="n", pady=(BANNER_TOP_MARGIN, 0))
        else:
            # Fallback if the image or Pillow is missing
            tk.Label(left, text="OpenLIB", font=FONT_TITLE,
                     fg=GOLD_COLOR, bg=CARD_COLOR).pack(pady=(BANNER_TOP_MARGIN, 0))

        # RIGHT SIDE: menu bar on top, page content below
        right = tk.Frame(self, bg=APP_BG)
        right.pack(side="left", fill="both", expand=True)

        self.nav_bar = tk.Frame(right, bg=CARD_COLOR)
        self.nav_bar.pack(fill="x")

        self.content = tk.Frame(right, bg=APP_BG)
        self.content.pack(fill="both", expand=True)

    def on_show(self):
        """Called every time the dashboard is displayed (after login)."""
        user = self.controller.current_user

        # Rebuild the menu, because it depends on who just logged in
        for widget in self.nav_bar.winfo_children():
            widget.destroy()

        for name in NAV_BY_ROLE[user["role"]]:
            # "n=name" is needed so each button remembers its own name
            tk.Button(self.nav_bar, text=name, font=FONT, bg=GOLD_COLOR, fg=DARK_TEXT,
                      relief="flat", cursor="hand2",
                      command=lambda n=name: self.show_section(n)
                      ).pack(side="left", padx=4, pady=8, ipadx=6)

        # Right side of the menu bar: logout button, then who is logged in
        tk.Button(self.nav_bar, text="Logout", font=FONT, bg=GOLD_COLOR, fg=DARK_TEXT,
                  relief="flat", cursor="hand2", command=self.controller.logout
                  ).pack(side="right", padx=8, pady=8, ipadx=6)
        self.user_label = tk.Label(self.nav_bar, font=FONT, fg=TEXT_COLOR, bg=CARD_COLOR)
        self.user_label.pack(side="right", padx=8)
        self.refresh_user_label()

        self.show_section("Books")

    def refresh_user_label(self):
        """Updates the 'username (role)' text in the menu bar (e.g. after a rename)."""
        user = self.controller.current_user
        if self.user_label is not None and user is not None:
            self.user_label.config(text=f"{user['username']} ({user['role']})")

    def clear_content(self):
        """Removes the page that is currently displayed."""
        for widget in self.content.winfo_children():
            widget.destroy()

    def refresh_user(self):
        """
        Re-reads the logged-in user from the database, because an Admin may have changed
        or deleted the account while this person was logged in.
        Returns True if everything is fine and the page may be shown, False if the
        dashboard has already reacted (logged out, or rebuilt the menu for the new role).
        """
        user = self.controller.current_user
        fresh = database.get_user(user["id"])

        # The account was deleted
        if isinstance(fresh, Status):
            messagebox.showerror("Account not found", "Your account no longer exists. You will be logged out.")
            self.controller.logout()
            return False

        old_role = user["role"]
        self.controller.current_user = dict(fresh)
        self.refresh_user_label()

        # The role changed: show the menu of the new role
        if fresh["role"] != old_role:
            messagebox.showinfo("Role changed", f"Your role is now {fresh['role']}.")
            self.on_show()
            return False
        return True

    def show_page(self, page_class, permission, **options):
        """
        Replaces the content area with a new page, after checking the permission.
        Parameters: page_class, permission (key of permissions.PERMISSIONS),
        options = extra values handed to the page (for example book_id=3).
        """
        if not self.refresh_user():
            return

        role = self.controller.current_user["role"]
        if not has_permission(role, permission):
            messagebox.showerror("Not allowed", "You do not have permission to open this page.")
            return

        self.clear_content()
        page = page_class(self.content, self.controller, **options)
        page.pack(fill="both", expand=True)

    def show_section(self, name, **options):
        """Shows one of the menu pages, e.g. show_section("Books")."""
        self.show_page(PAGES[name], PAGE_PERMISSIONS[name], **options)

    def show_book_details(self, book_id):
        """Shows the details page of one book (it is not in the menu)."""
        self.show_page(BookDetailsPage, "view_books", book_id=book_id)
