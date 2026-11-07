<p align="center">
  <img width="600" height="200" alt="OpenLIB Banner" src="https://github.com/user-attachments/assets/66d8cb4d-785e-4fc2-bda8-655648606167" />
</p>

<h1 align="center">
  <em>
    Library Management System
  </em>
</h1>

**OpenLIB** is a desktop library management application developed as part of an academic project. Built with Python, Tkinter, and SQLite, it aims to simplify library operations through an intuitive graphical interface.

The application provides tools for managing books, users, and borrowing activities, with role-based access control for Admins, Librarians, and Members. It also supports book searching, borrowing and returning books, and tracking active loans and due dates.

The project focuses on applying programming, database management, and graphical user interface development concepts to a practical, real-world scenario.

## Run it
    python main.py
Put `openliblogo.png` and `openlibbanner.png` (and optionally `openlibicon.png`) in an `assets/` folder
next to `main.py`. Without them the app still works and shows text instead of the pictures.
Pillow (`pip install pillow`) is only needed for the pictures. The database file `openlib.db` is created
next to `database.py`. The **first account registered becomes the Admin**, every other one is a Member.

## Files
| File | What it does |
|---|---|
| `main.py` | Main window, switches between Login / Register / Dashboard, closes the database on exit |
| `authentification.py` | Login and Register pages |
| `dashboard.py` | Banner + menu bar + the area where pages are shown. Checks permissions before showing a page |
| `books_page.py` | Books list, search and filters, Add / Edit / Delete buttons (Librarian, Admin) |
| `book_form.py` | Pop-up window to add or edit a book |
| `book_details_page.py` | One book's details. Members borrow from here |
| `my_loans_page.py` | Member: active loans (with Return) and loan history |
| `member_loans_page.py` | Librarian / Admin: all loans, filters (active, overdue, returned) |
| `members_page.py` | Librarian / Admin: list of Members |
| `users_page.py`, `user_form.py` | Admin: all users, create / edit / change role / delete |
| `account_page.py` | Everyone: see, edit and delete your own account |
| `permissions.py` | THE table of who may do what |
| `gui_helpers.py` | Images, tables, centered windows, permission re-check, background hashing |
| `database.py` | All SQL. Returns a `Status` for every failure |
| `helpers.py` | Validation, password hashing, friendly error messages |
| `status_codes.py`, `theme.py` | Status codes; colors and fonts |
