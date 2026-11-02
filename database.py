import sqlite3
from datetime import date, timedelta
from status_codes import Status
from helpers import *


conn = sqlite3.connect("openlib.db", autocommit=True)
conn.execute("PRAGMA foreign_keys = ON")
conn.autocommit = False
conn.row_factory = sqlite3.Row
cursor = conn.cursor()


# TABLES INITIALIZATION


def init():
    with conn:
        # Users table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK (LENGTH(username) BETWEEN 3 AND 50),
            password_hash TEXT NOT NULL,
            join_date DATE NOT NULL DEFAULT CURRENT_DATE,
            role TEXT NOT NULL CHECK (role IN ('Admin', 'Librarian', 'Member')),
            available_loans INTEGER NOT NULL DEFAULT 3
            CHECK (available_loans BETWEEN 0 AND 3)
        );"""
        )

        # Books table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL CHECK (LENGTH(title) BETWEEN 1 AND 100),
            author TEXT CHECK (LENGTH(author) BETWEEN 1 AND 50),
            genre TEXT NOT NULL CHECK (genre IN (
                'Action & Adventure', 'Biography & Memoir', 'Business & Economics',
                'Classics', 'Fantasy', 'Health & Wellness', 'History', 'Horror',
                'Mystery', 'Romance', 'Science Fiction', 'Self-Help',
                'Thriller & Suspense', 'True Crime', 'Travel'
            )),
            quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
            CONSTRAINT unique_title_per_author UNIQUE(title, author)
        );"""
        )

        cursor.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_books_title_noauthor
            ON books(title)
            WHERE author IS NULL;"""
        )

        # Loans table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            book_id INTEGER NOT NULL REFERENCES books(id),
            loan_date DATE NOT NULL,
            due_date DATE NOT NULL CHECK (due_date >= loan_date),
            returned_at DATE
        );"""
        )


# USERS TABLE FUNCTIONS


# Add a new user to the users table
def new_user(username, password_hash, role):
    try:
        with conn:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role,)
            )
    except sqlite3.IntegrityError as error:
        return get_users_error_type(str(error))
    except sqlite3.Error:
        return Status.DATABASE_ERROR
    return Status.SUCCESS


# Edit user's info
def edit_user(id, username=None, password_hash=None, role=None):
    cursor.execute("SELECT * FROM users WHERE id = ?", (id,))
    user_info = cursor.fetchone()

    # If the user doesn't exist
    if user_info is None:
        return Status.USER_NOT_FOUND
    
    conditions, values = [], []

    # Add the conditions and values depending on the available input arguments 
    if username is not None:
        conditions.append("username = ?")
        values.append(username)
    if password_hash is not None:
        conditions.append("password_hash = ?")
        values.append(password_hash)
    if role is not None:
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'Admin'")
        admin_count = cursor.fetchone()[0]

        # Prevent demoting the last Admin
        if user_info["role"] == "Admin" and admin_count == 1:
            return Status.FORBIDDEN
        conditions.append("role = ?")
        values.append(role)

    # If there is no input arguments
    if not conditions:
        return Status.NOTHING_TO_EDIT

    values.append(id)

    query = "UPDATE users SET " + ", ".join(conditions) + " WHERE id = ?"

    try:
        with conn:
            cursor.execute(query, values)
    except sqlite3.IntegrityError as error:
        return get_users_error_type(str(error))
    except sqlite3.Error:
        return Status.DATABASE_ERROR
    return Status.SUCCESS


def delete_user(id):
    try:
        cursor.execute("""
            SELECT *
            FROM users
            WHERE id = ?
        """, (id,))

        user = cursor.fetchone()

        # If the user doesn't exist
        if user is None:
            return Status.USER_NOT_FOUND
        # If the user is the admin
        elif user["role"] == "Admin":
            return Status.FORBIDDEN

        with conn:
            exit_status = return_all_books(id)
            # If all books have been returned successfully
            if exit_status != Status.SUCCESS:
                raise sqlite3.Error
            cursor.execute("DELETE FROM loans WHERE user_id = ?", (id,))
            cursor.execute("DELETE FROM users WHERE id = ?", (id,))

    except sqlite3.Error:
        return Status.DATABASE_ERROR
    return Status.SUCCESS


def search_users(active_user_role, id=None, username=None, role=None):
    if active_user_role in ["Admin", "Librarian"]:
        conditions, values = [], []

        query = "SELECT id, username, join_date"

        # Admins can check all users roles
        if active_user_role == "Admin":
            query += ", role"

        query += " FROM users"

        # Librarian can only check users with the role "Member"
        if active_user_role == "Librarian":
            role = "Member"

        # Add the conditions and values depending on the available input arguments 
        if id is not None:
            conditions.append("id = ?")
            values.append(id)
        if username is not None:
            conditions.append("username LIKE ?")
            values.append(f"%{username}%")
        if role is not None:
            conditions.append("role = ?")
            values.append(role)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY username"
        
        cursor.execute(query, values)
        return cursor.fetchall()
    else:
        return Status.FORBIDDEN


def login_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user_info = cursor.fetchone()

    # If the username exists
    if user_info:
        # If the password is correct
        if verify_secure_password(password, user_info["password_hash"]):
            cursor.execute("SELECT id, username, join_date, role FROM users WHERE username = ?", (username,))
            user_info = cursor.fetchone()

            return user_info
    return Status.UNAUTHORIZED


# BOOKS TABLE FUNCTIONS


def new_book(title, author, genre, quantity):
    try:
        # Make sure quantity is a number, not text
        try:
            quantity = int(quantity)
        except ValueError:
            return Status.INVALID_BOOK_QUANTITY
        with conn:
            cursor.execute(
                "INSERT INTO books (title, author, genre, quantity) VALUES (?, ?, ?, ?)",
                (title, author, genre, quantity),
            )
    except sqlite3.IntegrityError as error:
        return get_books_error_type(str(error))
    except sqlite3.Error:
        return Status.DATABASE_ERROR
    return Status.SUCCESS


def edit_book(id, title=None, author=None, genre=None, quantity=None):
    cursor.execute("SELECT * FROM books WHERE id = ?", (id,))

    book = cursor.fetchone()

    # If the book doesn't exist
    if book is None:
        return Status.BOOK_NOT_FOUND

    conditions, values = [], []

    if title is not None:
        conditions.append("title = ?")
        values.append(title)

    if author is not None:
        if author == "":
            conditions.append("author = NULL")
        else:
            conditions.append("author = ?")
            values.append(author)

    
    if genre is not None:
        conditions.append("genre = ?")
        values.append(genre)
    if quantity is not None:
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            return Status.INVALID_BOOK_QUANTITY
        if quantity < 0:
            return Status.INVALID_BOOK_QUANTITY
        
        conditions.append("quantity = ?")
        values.append(quantity)

    if not conditions:
        return Status.NOTHING_TO_EDIT

    values.append(id)

    query = "UPDATE books SET " + ", ".join(conditions) + " WHERE id = ?"

    try:
        with conn:
            cursor.execute(query, values)
    except sqlite3.IntegrityError as error:
        return get_books_error_type(str(error))
    except sqlite3.Error:
        return Status.DATABASE_ERROR
    return Status.SUCCESS


def delete_book(id):
    try:
        cursor.execute("""
            SELECT *
            FROM books
            WHERE id = ?
        """, (id,))

        book = cursor.fetchone()
        if book is None:
            return Status.BOOK_NOT_FOUND
        
        cursor.execute("""
            SELECT *
            FROM loans
            WHERE book_id = ?
            AND returned_at is NULL
        """, (id,))

        book_loans = cursor.fetchone()
        if book_loans is not None:
            return Status.BOOK_ACTUALLY_LOANED
        
        with conn:
            cursor.execute("DELETE FROM loans WHERE book_id = ?", (id,))
            cursor.execute("DELETE FROM books WHERE id = ?", (id,))
    except sqlite3.Error:
        return Status.DATABASE_ERROR
    return Status.SUCCESS


def search_books(id=None, title=None, author=None, genre=None):
    conditions, values = [], []

    if id is not None:
        conditions.append("id = ?")
        values.append(id)
    if title is not None:
        conditions.append("title LIKE ?")
        values.append(f"%{title}%")
    if author is not None:
        conditions.append("author LIKE ?")
        values.append(f"%{author}%")
    if genre is not None:
        conditions.append("genre = ?")
        values.append(genre)

    query = "SELECT * FROM books"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY title"

    cursor.execute(query, values)
    return cursor.fetchall()


# LOANS TABLE FUNCTIONS


def loan_book(user_id, book_id, loan_duration=14):
    # Check if the loan duration is valid
    try:
        loan_duration = int(loan_duration)
    except ValueError:
        return Status.INVALID_LOAN_DURATION
    if loan_duration < 0 or loan_duration > 21:
        return Status.INVALID_LOAN_DURATION
    
    try:
        with conn:
            # Check if the book is actively loaned by the user
            cursor.execute("""
                SELECT *
                FROM loans
                WHERE user_id = ?
                AND book_id = ?
                AND returned_at IS NULL
            """, (user_id, book_id))

            if cursor.fetchone() is not None:
                return Status.LOAN_ALREADY_EXISTS

            # Make sure the user exists
            cursor.execute("""
                SELECT *
                FROM users
                WHERE id = ?
            """, (user_id,))

            user = cursor.fetchone()
            if user is None:
                return Status.USER_NOT_FOUND

            # Make sure the book exists
            cursor.execute("""
                SELECT *
                FROM books
                WHERE id = ?
            """, (book_id,))

            book = cursor.fetchone()
            if book is None:
                return Status.BOOK_NOT_FOUND

            # Make sure the user still have available loans
            if user["available_loans"] == 0:
                return Status.MAX_LOANS_REACHED

            # Decrease the book's quantity by 1
            cursor.execute(
                """
                    UPDATE books
                    SET quantity = quantity - 1
                    WHERE id = ?
                    AND quantity > 0
                    RETURNING id
                """,
                (book_id,),
            )

            # Check if the book is out of stock
            if cursor.fetchone() is None:
                return Status.BOOK_OUT_OF_STOCK

            # Decrease the user's available loans by 1
            cursor.execute("""
                UPDATE users
                SET available_loans = available_loans - 1
                WHERE id = ?
                RETURNING id
            """, (user_id,))

            # If the user doesn't have any available loans
            if cursor.fetchone() is None:
                return Status.MAX_LOANS_REACHED

            loan_date = date.today()
            due_date = loan_date + timedelta(days=loan_duration)

            loan_date = loan_date.isoformat()
            due_date = due_date.isoformat()
            
            cursor.execute(
                "INSERT INTO loans (user_id, book_id, loan_date, due_date) VALUES (?, ?, ?, ?)",
                (user_id, book_id, loan_date, due_date,)
            )
    except sqlite3.IntegrityError as error:
        return get_loans_error_type(str(error))
    except sqlite3.Error:
        return Status.DATABASE_ERROR
    return Status.SUCCESS


def search_loans(id=None, username=None, title=None, author=None, genre=None, loan_date=None, due_date=None, returned_at=None, active_loans_only=False):
    conditions, values = [], []

    query = """
        SELECT loans.id, 
                users.username, 
                books.title, 
                books.author, 
                books.genre, 
                loans.loan_date, 
                loans.due_date, 
                loans.returned_at
        FROM loans
        INNER JOIN books ON loans.book_id = books.id
        INNER JOIN users ON loans.user_id = users.id
    """

    if id is not None:
        conditions.append("loans.id = ?")
        values.append(id)
    if username is not None:
        conditions.append("users.username LIKE ?")
        values.append(f"%{username}%")
    if title is not None:
        conditions.append("books.title LIKE ?")
        values.append(f"%{title}%")
    if author is not None:
        conditions.append("books.author LIKE ?")
        values.append(f"%{author}%")
    if genre is not None:
        conditions.append("books.genre = ?")
        values.append(genre)
    if loan_date is not None:
        conditions.append("loans.loan_date = ?")
        values.append(loan_date)
    if due_date is not None:
        conditions.append("loans.due_date = ?")
        values.append(due_date)

    if active_loans_only:
        conditions.append("loans.returned_at IS NULL")
    elif returned_at is not None :
        conditions.append("loans.returned_at = ?")
        values.append(returned_at)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY loan_date DESC"

    cursor.execute(query, values)
    return cursor.fetchall()


def return_book(id):
    try:
        with conn:
            returned_at = date.today().isoformat()

            cursor.execute("""
                UPDATE loans
                SET returned_at = ?
                WHERE id = ?
                AND returned_at IS NULL
                RETURNING user_id, book_id
            """, (returned_at, id,))

            loan = cursor.fetchone()

            # If the loan doesn't exist
            if loan is None:
                return Status.LOAN_NOT_FOUND

            # Increase the user's available loans by 1
            cursor.execute("""
                UPDATE users
                SET available_loans = MIN(3, available_loans + 1)
                WHERE id = ?
                RETURNING available_loans
            """, (loan["user_id"],))

            # Increase the book's quantity by 1
            cursor.execute("""
                UPDATE books
                SET quantity = quantity + 1
                WHERE id = ?
            """, (loan["book_id"],))

    except sqlite3.Error:
        return Status.DATABASE_ERROR
    return Status.SUCCESS


def return_all_books(user_id):
    try:
        cursor.execute("""
            SELECT *
            FROM loans
            WHERE user_id = ?
            AND returned_at IS NULL
        """, (user_id,))

        # Store all user's active loans in a variable
        user_loans = cursor.fetchall()
        # If the user has any existing active loans
        if user_loans:
            for loan in user_loans:
                returned_at = date.today().isoformat()

                # Return books by setting the return date
                cursor.execute("""
                    UPDATE loans
                    SET returned_at = ?
                    WHERE id = ?
                    AND returned_at IS NULL
                """, (returned_at, loan["id"],))

                # Increase the user's available loans by 1
                cursor.execute("""
                    UPDATE users
                    SET available_loans = MIN(3, available_loans + 1)
                    WHERE id = ?
                    RETURNING available_loans
                """, (loan["user_id"],))

                # Increase the book's quantity by 1
                cursor.execute("""
                    UPDATE books
                    SET quantity = quantity + 1
                    WHERE id = ?
                """, (loan["book_id"],))
                
        else:
            return Status.SUCCESS
    except sqlite3.Error:
        return Status.DATABASE_ERROR
    return Status.SUCCESS
