import tkinter as tk
from tkinter import ttk, messagebox
import database
from helpers import GENRES, get_status_message, to_whole_number
from gui_helpers import make_button, make_table, clear_table, selected_id, user_is_allowed
from permissions import has_permission
from status_codes import Status
from theme import *
from book_form import BookForm

ALL_GENRES = "All genres"  # first choice of the genre drop-down = "no genre filter"


class BooksPage(tk.Frame):
    """Books page: search/filter bar, table of books and the buttons under it.
    A new instance is created every time the user clicks "Books" in the menu,
    so data loaded in __init__ is always fresh."""

    def __init__(self, parent, controller):
        super().__init__(parent, bg=APP_BG)
        self.controller = controller
        # Logged-in user (a dict): self.controller.current_user["id"], ["username"], ["role"]
        role = self.controller.current_user["role"]
        # Librarians and Admins also get the Add / Edit / Delete buttons
        self.can_manage = has_permission(role, "manage_books")

        tk.Label(self, text="Books", font=FONT_TITLE, fg=CARD_COLOR, bg=APP_BG
                 ).pack(anchor="w", padx=20, pady=(15, 5))

        self.build_filter_bar()
        self.build_table()
        self.build_buttons()
        self.load_books()

    # ---------------------------------------------------------------- building the page

    def build_filter_bar(self):
        """Search box, genre drop-down, book id box, Search and Reset buttons (grid layout)."""
        bar = tk.Frame(self, bg=PANEL_BG, padx=10, pady=8)
        bar.pack(fill="x", padx=20, pady=5)

        # Row 0: small labels above each field
        tk.Label(bar, text="Title or author", font=FONT_SMALL, bg=PANEL_BG, fg=DARK_TEXT
                 ).grid(row=0, column=0, sticky="w")
        tk.Label(bar, text="Genre", font=FONT_SMALL, bg=PANEL_BG, fg=DARK_TEXT
                 ).grid(row=0, column=1, sticky="w", padx=(10, 0))
        tk.Label(bar, text="Book ID", font=FONT_SMALL, bg=PANEL_BG, fg=DARK_TEXT
                 ).grid(row=0, column=2, sticky="w", padx=(10, 0))

        # Row 1: the fields and the buttons
        self.search_entry = tk.Entry(bar, width=28, font=FONT)
        self.search_entry.grid(row=1, column=0, sticky="w", ipady=3)
        self.search_entry.bind("<Return>", lambda event: self.load_books())  # Enter = Search

        # state="readonly": the user can only pick from the list, not type
        self.genre_box = ttk.Combobox(bar, values=[ALL_GENRES] + GENRES, state="readonly", width=22)
        self.genre_box.set(ALL_GENRES)
        self.genre_box.grid(row=1, column=1, sticky="w", padx=(10, 0))

        self.id_entry = tk.Entry(bar, width=8, font=FONT)
        self.id_entry.grid(row=1, column=2, sticky="w", padx=(10, 0), ipady=3)
        self.id_entry.bind("<Return>", lambda event: self.load_books())

        make_button(bar, "Search", self.load_books).grid(row=1, column=3, padx=(15, 0))
        make_button(bar, "Reset", self.reset_filters).grid(row=1, column=4, padx=(8, 0))

    def build_table(self):
        """The table showing the books. A row is selected by clicking it."""
        # Members see how many copies can be borrowed; staff see the stock
        quantity_heading = "In Stock" if self.can_manage else "Available"
        table_frame, self.table = make_table(self, [
            ("ID", 50), ("Title", 260), ("Author", 170), ("Genre", 150), (quantity_heading, 80),
        ])
        table_frame.pack(fill="both", expand=True, padx=20, pady=5)
        self.table.bind("<Double-1>", lambda event: self.view_selected_book())  # double click = View

        self.count_label = tk.Label(self, text="", font=FONT_SMALL, fg=DARK_TEXT, bg=APP_BG)
        self.count_label.pack(anchor="w", padx=20)

    def build_buttons(self):
        """The buttons under the table. Add/Edit/Delete only exist for Librarians and Admins."""
        buttons = tk.Frame(self, bg=APP_BG)
        buttons.pack(fill="x", padx=20, pady=(5, 12))

        make_button(buttons, "View Book", self.view_selected_book).pack(side="left", padx=(0, 8))
        if self.can_manage:
            make_button(buttons, "Add Book", self.add_book).pack(side="left", padx=(0, 8))
            make_button(buttons, "Edit Book", self.edit_book).pack(side="left", padx=(0, 8))
            make_button(buttons, "Delete Book", self.delete_book).pack(side="left", padx=(0, 8))

    # ---------------------------------------------------------------- searching

    def reset_filters(self):
        """Empties every filter and shows all books again."""
        self.search_entry.delete(0, tk.END)
        self.id_entry.delete(0, tk.END)
        self.genre_box.set(ALL_GENRES)
        self.load_books()

    def find_books(self, text, genre, book_id):
        """
        Asks the database for the books matching the filters.
        The search text is looked for in the title AND in the author.
        Parameters: text (may be ""), genre (None = any), book_id (None = any).
        Returns a list of books, or a Status if the database failed.
        """
        if text == "":
            return database.search_books(id=book_id, genre=genre)

        by_title = database.search_books(id=book_id, title=text, genre=genre)
        by_author = database.search_books(id=book_id, author=text, genre=genre)
        for result in (by_title, by_author):
            if isinstance(result, Status):
                return result

        # Join both lists without showing a book twice
        books_by_id = {}
        for book in list(by_title) + list(by_author):
            books_by_id[book["id"]] = book
        return sorted(books_by_id.values(), key=lambda book: book["title"].lower())

    def load_books(self):
        """Reads the filters, searches the database and fills the table."""
        text = self.search_entry.get().strip()

        genre = self.genre_box.get()
        if genre == ALL_GENRES:
            genre = None  # None = do not filter by genre

        book_id = None
        id_text = self.id_entry.get().strip()
        if id_text != "":
            book_id = to_whole_number(id_text, 1, 10 ** 9)
            if book_id is None:
                messagebox.showerror("Invalid book ID", "The book ID must be a whole number (for example 12).")
                return

        books = self.find_books(text, genre, book_id)
        if isinstance(books, Status):
            messagebox.showerror("Error", get_status_message(books))
            return

        clear_table(self.table)
        for book in books:
            author = book["author"] if book["author"] else "Unknown"
            # iid = the book id: it lets us know which book a selected row is
            self.table.insert("", "end", iid=str(book["id"]),
                              values=(book["id"], book["title"], author, book["genre"], book["quantity"]))
        self.count_label.config(text=f"{len(books)} book(s) found")

    # ---------------------------------------------------------------- buttons

    def view_selected_book(self):
        """Opens the details page of the selected book."""
        book_id = selected_id(self.table, "book")
        if book_id is not None:
            self.controller.dashboard.show_book_details(book_id)

    def add_book(self):
        """Opens the empty 'Add Book' form."""
        if not user_is_allowed(self.controller, "manage_books"):
            return
        BookForm(self, self.controller, book=None, on_saved=self.load_books)

    def edit_book(self):
        """Opens the 'Edit Book' form filled with the selected book."""
        if not user_is_allowed(self.controller, "manage_books"):
            return
        book_id = selected_id(self.table, "book")
        if book_id is None:
            return
        found = database.search_books(id=book_id)
        if isinstance(found, Status) or not found:
            messagebox.showerror("Error", get_status_message(Status.BOOK_NOT_FOUND))
            self.load_books()
            return
        BookForm(self, self.controller, book=found[0], on_saved=self.load_books)

    def delete_book(self):
        """Deletes the selected book after asking for confirmation."""
        if not user_is_allowed(self.controller, "manage_books"):
            return
        book_id = selected_id(self.table, "book")
        if book_id is None:
            return
        title = self.table.item(str(book_id), "values")[1]
        sure = messagebox.askyesno("Delete book",
                                   f'Delete "{title}"?\nIts returned-loan history will be deleted too.')
        if not sure:
            return

        status = database.delete_book(book_id)
        if status == Status.SUCCESS:
            messagebox.showinfo("Deleted", "The book was deleted.")
        else:
            messagebox.showerror("Could not delete", get_status_message(status))
        self.load_books()
