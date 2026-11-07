import hashlib
import hmac
import os
from datetime import date
from status_codes import Status

# The genres accepted by the database (must match the CHECK list in database.init)
GENRES = [
    "Action & Adventure", "Biography & Memoir", "Business & Economics",
    "Classics", "Fantasy", "Health & Wellness", "History", "Horror",
    "Mystery", "Romance", "Science Fiction", "Self-Help",
    "Thriller & Suspense", "True Crime", "Travel",
]

# Upper limits used when validating whole numbers
MAX_BOOK_QUANTITY = 10000
MAX_LOAN_DURATION = 21


# VALIDATION
def to_whole_number(value, minimum, maximum):
    """
    Safely converts a value to a whole number (int).
    Parameters: value (int or text like "5"), minimum and maximum allowed values.
    Returns the int, or None when the value is not acceptable.
    Rejected: None, True/False, decimals such as 2.5, text that is not a number,
    and numbers outside the minimum..maximum range.
    """
    # bool is a kind of int in Python, so it must be rejected explicitly
    if value is None or isinstance(value, (bool, float)):
        return None
    try:
        number = int(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if number < minimum or number > maximum:
        return None
    return number


def escape_like(text):
    """
    Prepares text for a SQL "LIKE ? ESCAPE '\\'" search so that the characters
    % and _ are searched literally instead of acting as wildcards.
    """
    text = text.replace("\\", "\\\\")  # the escape character itself first
    text = text.replace("%", "\\%")
    text = text.replace("_", "\\_")
    return text


def loan_status(loan):
    """
    Returns "Returned", "Overdue" or "Active" for a loan row
    (a row from database.search_loans).
    """
    if loan["returned_at"] is not None:
        return "Returned"
    # Dates are stored as YYYY-MM-DD text, so comparing the text compares the dates
    if loan["due_date"] < date.today().isoformat():
        return "Overdue"
    return "Active"


def validate_password_strength(password: str) -> Status:
    """
    Validates password strength constraints:
    - At least 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    Returns Status.SUCCESS if valid, else Status.INVALID_PASSWORD.
    """
    if len(password) < 8:
        return Status.INVALID_PASSWORD
    if not any(char.isupper() for char in password):
        return Status.INVALID_PASSWORD
    if not any(char.islower() for char in password):
        return Status.INVALID_PASSWORD
    if not any(char.isdigit() for char in password):
        return Status.INVALID_PASSWORD
    return Status.SUCCESS


def get_status_message(status: Status) -> str:
    """Translates Status enums into user-friendly UI error messages."""
    messages = {
        # Users
        Status.USER_NOT_FOUND: "This user does not exist.",
        Status.INVALID_PASSWORD: "Password must be at least 8 characters with upper, lower, and numbers.",
        Status.USERNAME_ALREADY_EXISTS: "This username is already taken.",
        Status.INVALID_USERNAME: "Username must be between 3 and 50 characters.",
        Status.INVALID_ROLE: "Invalid role.",
        Status.UNAUTHORIZED: "Invalid username or password.",
        # Books
        Status.BOOK_NOT_FOUND: "This book does not exist.",
        Status.BOOK_ALREADY_EXISTS: "This book (same title and author) already exists.",
        Status.INVALID_TITLE: "Title must be between 1 and 100 characters.",
        Status.INVALID_AUTHOR_NAME: "Author must be between 1 and 50 characters.",
        Status.INVALID_GENRE: "Please choose a valid genre.",
        Status.INVALID_BOOK_QUANTITY: f"Quantity must be a whole number between 0 and {MAX_BOOK_QUANTITY}.",
        # Loans
        Status.LOAN_NOT_FOUND: "This loan does not exist or was already returned.",
        Status.LOAN_ALREADY_EXISTS: "You already have this book on loan.",
        Status.BOOK_OUT_OF_STOCK: "No copies of this book are available right now.",
        Status.BOOK_ACTUALLY_LOANED: "This book cannot be deleted while copies are on loan.",
        Status.INVALID_LOAN_DURATION: f"Loan duration must be a whole number of days (maximum {MAX_LOAN_DURATION}).",
        Status.INVALID_DUE_DATE: "The due date is invalid.",
        Status.MAX_LOANS_REACHED: "You have reached the maximum number of loans (3).",
        # Permissions
        Status.FORBIDDEN: "You are not allowed to do this. (Admin accounts cannot be deleted, "
                          "and the last Admin cannot be demoted.)",
        Status.NOTHING_TO_EDIT: "Nothing was changed.",
        Status.DATABASE_ERROR: "Database error. Please try again later.",
    }
    return messages.get(status, "An unexpected error occurred.")


# SECURITY


def create_secure_password(password):
    # Create a highly secure, random 16-byte salt
    salt = os.urandom(16)

    # Hash the password by running SHA-256 exactly 600,000 times (a commonly recommended iteration count)
    #    This makes guessing passwords much slower and more expensive for an attacker.
    hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)

    return f"pbkdf2_sha256:600000:{salt.hex()}:{hash.hex()}"


def verify_secure_password(input_password, stored_password_hash):
    try:
        # Split stored password hash into 4 string variables with : 
        algo, iterations, salt_hex, hash_hex = stored_password_hash.split(":")

        # Convert hex strings back to raw computer bytes
        salt = bytes.fromhex(salt_hex)
        original_hash = bytes.fromhex(hash_hex)

        # Hash the input password
        new_hash = hashlib.pbkdf2_hmac("sha256", input_password.encode("utf-8"), salt, int(iterations))

        # Compares both hashes to see if they match
        return hmac.compare_digest(original_hash, new_hash)
    
    except (ValueError, TypeError, AttributeError):
        # If the string is corrupted, broken, or empty, fail gracefully instead of crashing
        return False


# ERROR HANDLING


def get_users_error_type(error_msg):
    if "UNIQUE constraint failed: users.username" in error_msg:
        return Status.USERNAME_ALREADY_EXISTS
    elif "CHECK constraint failed: LENGTH(username) BETWEEN 3 AND 50" in error_msg:
        return Status.INVALID_USERNAME
    elif "CHECK constraint failed: role IN ('Admin', 'Librarian', 'Member')" in error_msg:
        return Status.INVALID_ROLE
    return Status.DATABASE_ERROR


def get_books_error_type(error_msg):
    if "UNIQUE constraint failed: books" in error_msg:
        return Status.BOOK_ALREADY_EXISTS
    elif "CHECK constraint failed: LENGTH(title) BETWEEN 1 AND 100" in error_msg:
        return Status.INVALID_TITLE
    elif "CHECK constraint failed: LENGTH(author) BETWEEN 1 AND 50" in error_msg:
        return Status.INVALID_AUTHOR_NAME
    elif "CHECK constraint failed: genre IN" in error_msg:
        return Status.INVALID_GENRE
    elif "CHECK constraint failed: quantity >= 0" in error_msg:
        return Status.INVALID_BOOK_QUANTITY
    return Status.DATABASE_ERROR


def get_loans_error_type(error_msg):
    if "CHECK constraint failed: due_date >= loan_date" in error_msg:
        return Status.INVALID_DUE_DATE
    return Status.DATABASE_ERROR
