import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

import database
from helpers import create_secure_password, validate_password_strength
from status_codes import Status

GENRES = [
    "Action & Adventure", "Biography & Memoir", "Business & Economics", "Classics",
    "Fantasy", "Health & Wellness", "History", "Horror", "Mystery", "Romance",
    "Science Fiction", "Self-Help", "Thriller & Suspense", "True Crime", "Travel",
]
ROLES = ["Admin", "Librarian", "Member"]
ALL = "All"
DEFAULT_LOAN_DAYS, MAX_LOAN_DAYS, MAX_LOANS_PER_MEMBER = 14, 21, 3
RED = "#c0392b"

MESSAGES = {
    Status.USER_NOT_FOUND: "This user does not exist.",
    Status.USERNAME_ALREADY_EXISTS: "This username is already taken.",
    Status.INVALID_USERNAME: "The username must contain between 3 and 50 characters.",
    Status.INVALID_PASSWORD: "Password must be at least 8 characters with upper, lower and a digit.",
    Status.INVALID_ROLE: "Invalid role.",
    Status.INVALID_CREDENTIALS: "Incorrect username or password.",
    Status.BOOK_NOT_FOUND: "This book does not exist.",
    Status.BOOK_ALREADY_EXISTS: "A book with the same title and author already exists.",
    Status.INVALID_TITLE: "The title must contain between 1 and 100 characters.",
    Status.INVALID_AUTHOR_NAME: "The author must contain between 1 and 50 characters.",
    Status.INVALID_GENRE: "Please choose a valid genre.",
    Status.INVALID_BOOK_QUANTITY: "The quantity must be a whole number, 0 or more.",
    Status.LOAN_NOT_FOUND: "Loan not found, or the book has already been returned.",
    Status.LOAN_ALREADY_EXISTS: "This member already has this book on loan.",
    Status.BOOK_ALREADY_RETURNED: "This book has already been returned.",
    Status.BOOK_OUT_OF_STOCK: "No copy of this book is currently available.",
    Status.BOOK_ACTUALLY_LOANED: "This book is currently on loan and cannot be deleted.",
    Status.INVALID_LOAN_DURATION: f"The loan duration must be between 0 and {MAX_LOAN_DAYS} days.",
    Status.INVALID_DUE_DATE: "The due date cannot be before the loan date.",
    Status.MAX_LOANS_REACHED: f"This member already has {MAX_LOANS_PER_MEMBER} active loans.",
    Status.MAX_LOANS_EXCEEDED: f"This member already has {MAX_LOANS_PER_MEMBER} active loans.",
    Status.UNAUTHORIZED: "Incorrect username or password.",
    Status.FORBIDDEN: "This action is not allowed (administrator accounts are protected).",
    Status.DATABASE_ERROR: "A database error occurred. Please try again.",
    Status.INVALID_INPUT: "Invalid input.",
    Status.NOTHING_TO_EDIT: "Nothing to change.",
}


# ------------------------------------------------------------------- helpers
def report(status, parent=None):
    """Return True when the backend succeeded, otherwise show its error and return False."""
    if status == Status.SUCCESS:
        return True
    messagebox.showerror("OpenLIB", MESSAGES.get(status, "Unexpected error."), parent=parent)
    return False


def rows_or_empty(result):
    """Search functions return a list of rows, or a Status (e.g. FORBIDDEN)."""
    return [] if isinstance(result, Status) else result


def loan_state(loan, today=None):
    """'Returned', 'Overdue' or 'Active' for a row of search_loans()."""
    if loan["returned_at"]:
        return "Returned"
    limit = (today or date.today()).isoformat()
    return "Overdue" if loan["due_date"] < limit else "Active"


def days_late(loan, today=None):
    due = date.fromisoformat(loan["due_date"])
    return max(0, ((today or date.today()) - due).days)


def no_users_yet():
    """First start only: database.py has no 'count users' function, so one direct query."""
    return database.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


# -------------------------------------------------------------------- dialogs
class FormDialog(tk.Toplevel):
    """Generic modal form. `fields` is a list of dicts: key, label, kind, value, choices.

    kind = "text" (default), "password", "choice" (read-only list) or "spin" (from_, to).
    After the window closes, `result` is a dict {key: text} or None if cancelled.
    """

    def __init__(self, parent, title, fields, ok_text="Save"):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.result = None
        self._vars, self._kinds = {}, {}

        body = ttk.Frame(self, padding=16)
        body.grid()
        for row, field in enumerate(fields):
            kind = field.get("kind", "text")
            var = tk.StringVar(value=str(field.get("value", "")))
            ttk.Label(body, text=field["label"]).grid(row=row, column=0, sticky="w",
                                                      pady=5, padx=(0, 12))
            if kind == "choice":
                widget = ttk.Combobox(body, textvariable=var, values=field["choices"],
                                      state="readonly", width=38)
            elif kind == "spin":
                widget = ttk.Spinbox(body, textvariable=var, from_=field["from_"],
                                     to=field["to"], width=8)
            else:
                widget = ttk.Entry(body, textvariable=var, width=40,
                                   show="*" if kind == "password" else "")
            widget.grid(row=row, column=1, sticky="w")
            if row == 0:
                widget.focus_set()
            self._vars[field["key"]], self._kinds[field["key"]] = var, kind

        buttons = ttk.Frame(body)
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text=ok_text, command=self._submit).pack(side="right", padx=6)
        self.bind("<Return>", lambda _e: self._submit())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.wait_visibility()  # grab_set() fails on Linux if the window is not visible yet
        self.grab_set()
        self.wait_window()

    def _submit(self):
        self.result = {key: (var.get() if self._kinds[key] == "password" else var.get().strip())
                       for key, var in self._vars.items()}
        self.destroy()


def password_fields(existing_account=False):
    """Form fields for a (new) password and its confirmation."""
    label = "New password (empty = keep)" if existing_account else "Password"
    return [{"key": "password", "label": label, "kind": "password"},
            {"key": "confirm", "label": "Confirm password", "kind": "password"}]


def check_passwords(data, required=True):
    """Validate the password pair of a form. Returns True if OK (else shows an error)."""
    if not data["password"] and not required:
        return True
    if validate_password_strength(data["password"]) != Status.SUCCESS:
        return report(Status.INVALID_PASSWORD)
    if data["password"] != data["confirm"]:
        messagebox.showerror("OpenLIB", "The two passwords do not match.")
        return False
    return True


# ----------------------------------------------------------------------- tabs
class BaseTab(ttk.Frame):
    """Generic tab: filter bar + table + action buttons.

    Subclasses provide columns(), build_filters(), fetch(), display() and buttons().
    """

    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.user = app.user
        self.rows = {}
        self.filter_vars = []

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 8))
        self.build_filters(bar)

        zone = ttk.Frame(self)
        zone.pack(fill="both", expand=True)
        columns = self.columns()
        self.table = ttk.Treeview(zone, columns=[c[0] for c in columns], show="headings",
                                  selectmode="browse")
        for key, heading, width, anchor in columns:
            self.table.heading(key, text=heading)
            self.table.column(key, width=width, anchor=anchor)
        scroll = ttk.Scrollbar(zone, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        self.table.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.table.tag_configure("alert", foreground=RED)

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(8, 0))
        for text, command in self.buttons():
            ttk.Button(actions, text=text, command=command).pack(side="left", padx=(0, 6))

        for var in self.filter_vars:  # live filtering
            var.trace_add("write", lambda *_: self.refresh())
        self.refresh()

    # -- to be provided by subclasses
    def columns(self):
        raise NotImplementedError

    def build_filters(self, bar):
        """Create the filter widgets and append their variables to self.filter_vars."""

    def fetch(self):
        raise NotImplementedError

    def display(self, row):
        """Return (values, tags) for one row."""
        raise NotImplementedError

    def buttons(self):
        return []

    # -- common behaviour
    def add_filter_entry(self, bar, label, width=20):
        var = tk.StringVar()
        ttk.Label(bar, text=label).pack(side="left")
        ttk.Entry(bar, textvariable=var, width=width).pack(side="left", padx=(4, 12))
        self.filter_vars.append(var)
        return var

    def refresh(self):
        self.rows = {}
        self.table.delete(*self.table.get_children())
        for row in self.fetch():
            iid = str(row["id"])
            self.rows[iid] = row
            values, tags = self.display(row)
            self.table.insert("", "end", iid=iid, values=values, tags=tags)

    def selected(self):
        """The selected row, or None (after asking the user to select one)."""
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo("OpenLIB", "Select a row in the table first.")
            return None
        return self.rows[selection[0]]

    def apply(self, status):
        """Show the backend error if any; refresh every tab when the action succeeded."""
        if report(status, self):
            self.app.refresh_all()
            return True
        return False


class BooksTab(BaseTab):
    def columns(self):
        return [("id", "ID", 50, "center"), ("title", "Title", 290, "w"),
                ("author", "Author", 180, "w"), ("genre", "Genre", 170, "w"),
                ("quantity", "Available", 80, "center")]

    def build_filters(self, bar):
        self.title_var = self.add_filter_entry(bar, "Title:", 22)
        self.author_var = self.add_filter_entry(bar, "Author:", 18)
        self.genre_var = tk.StringVar(value=ALL)
        ttk.Label(bar, text="Genre:").pack(side="left")
        ttk.Combobox(bar, textvariable=self.genre_var, values=[ALL] + GENRES,
                     state="readonly", width=20).pack(side="left", padx=4)
        self.filter_vars.append(self.genre_var)

    def fetch(self):
        genre = self.genre_var.get()
        return database.search_books(title=self.title_var.get().strip() or None,
                                     author=self.author_var.get().strip() or None,
                                     genre=None if genre == ALL else genre)

    def display(self, book):
        values = (book["id"], book["title"], book["author"] or "", book["genre"],
                  book["quantity"])
        return values, ("alert",) if book["quantity"] == 0 else ()

    def buttons(self):
        if not self.app.is_staff:
            return []
        return [("Add book", self.add), ("Edit", self.edit), ("Delete", self.delete)]

    def form(self, title, book=None):
        value = lambda key, default="": (book[key] if book and book[key] is not None else default)
        return FormDialog(self, title, [
            {"key": "title", "label": "Title", "value": value("title")},
            {"key": "author", "label": "Author", "value": value("author")},
            {"key": "genre", "label": "Genre", "kind": "choice", "choices": GENRES,
             "value": value("genre", GENRES[0])},
            {"key": "quantity", "label": "Available copies", "kind": "spin", "from_": 0,
             "to": 999, "value": value("quantity", 1)},
        ]).result

    def add(self):
        data = self.form("Add a book")
        if data:
            self.apply(database.new_book(data["title"], data["author"] or None,
                                         data["genre"], data["quantity"]))

    def edit(self):
        book = self.selected()
        if book is None:
            return
        data = self.form("Edit book", book)
        if data:
            self.apply(database.edit_book(book["id"], data["title"], data["author"],
                                          data["genre"], data["quantity"]))

    def delete(self):
        book = self.selected()
        if book and messagebox.askyesno("OpenLIB", f"Delete « {book['title']} » and its loan history?"):
            self.apply(database.delete_book(book["id"]))


class UsersTab(BaseTab):
    """Admin: every account. Librarian: members only (enforced by database.search_users)."""

    def columns(self):
        columns = [("id", "ID", 50, "center"), ("username", "Username", 220, "w"),
                   ("join_date", "Member since", 120, "center")]
        if self.user["role"] == "Admin":
            columns.append(("role", "Role", 110, "center"))
        return columns

    def build_filters(self, bar):
        self.name_var = self.add_filter_entry(bar, "Username:", 24)
        self.role_var = tk.StringVar(value=ALL)
        if self.user["role"] == "Admin":
            ttk.Label(bar, text="Role:").pack(side="left")
            ttk.Combobox(bar, textvariable=self.role_var, values=[ALL] + ROLES,
                         state="readonly", width=12).pack(side="left", padx=4)
            self.filter_vars.append(self.role_var)

    def fetch(self):
        role = self.role_var.get()
        return rows_or_empty(database.search_users(
            self.user["role"], username=self.name_var.get().strip() or None,
            role=None if role == ALL else role))

    def display(self, user):
        values = [user["id"], user["username"], user["join_date"]]
        if self.user["role"] == "Admin":
            values.append(user["role"])
        return values, ()

    def buttons(self):
        label = "user" if self.user["role"] == "Admin" else "member"
        return [(f"Add {label}", self.add), ("Edit", self.edit), ("Delete", self.delete)]

    def add(self):
        fields = [{"key": "username", "label": "Username"}]
        fields += password_fields()
        if self.user["role"] == "Admin":
            fields.append({"key": "role", "label": "Role", "kind": "choice",
                           "choices": ROLES, "value": "Member"})
        data = FormDialog(self, "Add an account", fields, ok_text="Create").result
        if data and check_passwords(data):
            role = data.get("role", "Member")
            self.apply(database.new_user(data["username"],
                                         create_secure_password(data["password"]), role))

    def edit(self):
        user = self.selected()
        if user is None:
            return
        is_admin = self.user["role"] == "Admin"
        fields = [{"key": "username", "label": "Username", "value": user["username"]}]
        fields += password_fields(existing_account=True)
        if is_admin:
            fields.append({"key": "role", "label": "Role", "kind": "choice",
                           "choices": ROLES, "value": user["role"]})
        data = FormDialog(self, "Edit account", fields).result
        if not data or not check_passwords(data, required=False):
            return
        changes = {}
        if data["username"] != user["username"]:
            changes["username"] = data["username"]
        if data["password"]:
            changes["password_hash"] = create_secure_password(data["password"])
        # Only send the role when it changes: edit_user() refuses any role argument
        # for the last administrator, even if the role is the same.
        if is_admin and data["role"] != user["role"]:
            changes["role"] = data["role"]
        if self.apply(database.edit_user(user["id"], **changes)):
            if user["id"] == self.user["id"] and "username" in changes:
                self.app.user["username"] = changes["username"]
                self.app.update_header()

    def delete(self):
        user = self.selected()
        if user is None:
            return
        if user["id"] == self.user["id"]:
            messagebox.showinfo("OpenLIB", "You cannot delete your own account.")
        elif messagebox.askyesno("OpenLIB", f"Delete « {user['username']} » ? Their active "
                                            "loans will be returned and their history removed."):
            self.apply(database.delete_user(user["id"]))


class LoansTab(BaseTab):
    """Staff: all loans, with New loan / Return (supports ID-based filtering). 
       Member: own active loans or history, read only."""

    def columns(self):
        return [("id", "ID", 50, "center"), ("user_id", "User ID", 70, "center"), 
                ("book_id", "Book ID", 70, "center"), ("due_date", "Due", 100, "center"), 
                ("returned_at", "Returned", 100, "center"), ("state", "Status", 90, "center")]

    def build_filters(self, bar):
        if self.app.is_staff:
            self.user_id_var = self.add_filter_entry(bar, "User ID:", 10)
            self.book_id_var = self.add_filter_entry(bar, "Book ID:", 10)
        else:
            self.active_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(bar, text="Active loans only", variable=self.active_var).pack(
                side="left", padx=10)
            self.filter_vars.append(self.active_var)

    def fetch(self):
        if self.app.is_staff:
            u_id = self.user_id_var.get().strip()
            b_id = self.book_id_var.get().strip()
            
            user_id_val = int(u_id) if u_id.isdigit() else None
            book_id_val = int(b_id) if b_id.isdigit() else None
            
            return database.lister_emprunts_admin(user_id=user_id_val, book_id=book_id_val)
        else:
            user_id = self.user["id"]
            if self.active_var.get():
                return database.lister_emprunts_actifs_membre(user_id)
            else:
                return database.historique_emprunts_membre(user_id)

    def display(self, loan):
        loan_id, user_id, book_id, due_date, returned_at = loan
        
        loan_dict = {"due_date": due_date, "returned_at": returned_at}
        state = loan_state(loan_dict)
        
        values = (loan_id, user_id, book_id, due_date, returned_at or "", state)
        return values, ("alert",) if state == "Overdue" else ()

    def buttons(self):
        if self.app.is_staff:
            return [
                ("New loan", self.new_loan), 
                ("Return book", self.return_book),
                ("Filtrer (Admin)", self.filtrer_admin_action)
            ]
        else:
            return [
                ("Voir emprunts actifs", self.voir_actifs),
                ("Voir historique complet", self.voir_historique)
            ]

    def filtrer_admin_action(self):
        self.refresh()
        messagebox.showinfo("OpenLIB", "Liste des emprunts filtrée avec succès.")

    def voir_actifs(self):
        user_id = self.user["id"]
        resultats = database.lister_emprunts_actifs_membre(user_id)
        if not resultats:
            messagebox.showinfo("Mes emprunts actifs", "Vous n'avez aucun livre emprunté actuellement.")
        else:
            texte = "\n".join([f"Emprunt ID: {r[0]} | Livre ID: {r[1]} | Date limite: {r[2]}" for r in resultats])
            messagebox.showinfo("Mes emprunts actifs", texte)

    def voir_historique(self):
        user_id = self.user["id"]
        resultats = database.historique_emprunts_membre(user_id)
        if not resultats:
            messagebox.showinfo("Historique", "Vous n'avez aucun historique d'emprunt.")
        else:
            texte = "\n".join([f"ID: {r[0]} | Livre: {r[1]} | Échéance: {r[2]} | Rendu: {r[3] if r[3] else 'Non rendu'}" for r in resultats])
            messagebox.showinfo("Historique complet", texte)

    def new_loan(self):
        members = rows_or_empty(database.search_users(self.user["role"], role="Member"))
        books = [b for b in database.search_books() if b["quantity"] > 0]
        
        if not members or not books:
            messagebox.showinfo("OpenLIB", "Il faut au moins un membre et un livre disponible.")
            return
            
        member_choices = {f"{m['id']} - {m['username']}": m["id"] for m in members}
        book_choices = {f"{b['id']} - {b['title']}": b["id"] for b in books}
        
        data = FormDialog(self, "New loan", [
            {"key": "member", "label": "Member", "kind": "choice", "choices": list(member_choices)},
            {"key": "book", "label": "Book", "kind": "choice", "choices": list(book_choices)},
            {"key": "days", "label": "Duration (days)", "kind": "spin", "from_": 1, 
             "to": MAX_LOAN_DAYS, "value": DEFAULT_LOAN_DAYS},
        ], ok_text="Lend").result
        
        if not data:
            return
        if not data["member"] or not data["book"]:
            messagebox.showwarning("OpenLIB", "Veuillez choisir un membre et un livre.")
            return
            
        user_id = member_choices[data["member"]]
        book_id = book_choices[data["book"]]
        duree_jours = int(data["days"])
        
        resultat = database.emprunter_livre(user_id, book_id, duree_jours)
        
        if resultat is not None:
            messagebox.showinfo("Succès", "Emprunt enregistré avec succès !")
            self.refresh()
        else:
            messagebox.showerror("Erreur", "Impossible d'effectuer l'emprunt (livre épuisé ou erreur).")

    def return_book(self):
        loan = self.selected()
        if loan is None:
            return
            
        loan_id, user_id, book_id, due_date, returned_at = loan
        
        if returned_at:
            messagebox.showinfo("OpenLIB", MESSAGES[Status.BOOK_ALREADY_RETURNED])
            return
            
        resultat_book_id = database.retourner_livre(loan_id)
        
        if resultat_book_id is not None:
            messagebox.showinfo("Succès", "Livre retourné avec succès !")
            self.refresh()
        else:
            messagebox.showerror("Erreur", "Impossible d'enregistrer le retour de ce livre.")

# ------------------------------------------------------------------ dashboard
class MainFrame(ttk.Frame):
    """Dashboard shown after login. `controller` is the application window (main.py):
    it provides `current_user` (dict) and `logout()`."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.user = controller.current_user
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", rowheight=24)

        head = ttk.Frame(self, padding=(14, 10, 14, 4))
        head.pack(fill="x")
        ttk.Label(head, text="OpenLIB", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(head, text="Log out", command=controller.logout).pack(side="right")
        self.who = tk.StringVar()
        ttk.Label(head, textvariable=self.who).pack(side="right", padx=12)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8)
        role = self.user["role"]
        tabs = [(BooksTab, "Books")]
        if role == "Admin":
            tabs.append((UsersTab, "Users"))
        elif role == "Librarian":
            tabs.append((UsersTab, "Members"))
        tabs.append((LoansTab, "Loans" if self.is_staff else "My loans"))
        self.pages = []
        for tab_class, title in tabs:
            page = tab_class(notebook, self)
            notebook.add(page, text=title)
            self.pages.append(page)
        notebook.bind("<<NotebookTabChanged>>", lambda _e: self.refresh())

        self.stats = tk.StringVar()
        ttk.Label(self, textvariable=self.stats, relief="sunken", anchor="w",
                  padding=(8, 3)).pack(fill="x", side="bottom")
        self.update_header()
        self.refresh()

    @property
    def is_staff(self):
        return self.user["role"] in ("Admin", "Librarian")

    def refresh_all(self):
        self.refresh()

    def update_header(self):
        self.who.set(f"{self.user['username']}  ({self.user['role']})")

    def refresh(self):
        """Reload every tab and the statistics bar."""
        for page in self.pages:
            page.refresh()
        books = database.search_books()
        if self.is_staff:
            active = database.search_loans(active_loans_only=True)
            late = sum(loan_state(l) == "Overdue" for l in active)
            self.stats.set(f"{len(books)} titles  |  {sum(b['quantity'] for b in books)} copies "
                           f"available  |  {len(active)} active loans  |  {late} overdue")
        else:
            mine = [l for l in database.search_loans(username=self.user["username"],
                                                     active_loans_only=True)
                    if l["username"].lower() == self.user["username"].lower()]
            late = sum(loan_state(l) == "Overdue" for l in mine)
            self.stats.set(f"{len(books)} titles in the catalogue  |  your active loans: "
                           f"{len(mine)} / {MAX_LOANS_PER_MEMBER}  |  {late} overdue")
