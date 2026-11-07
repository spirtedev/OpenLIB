import hashlib
import hmac
import os
from status_codes import Status
# VALIDATION
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
        Status.INVALID_PASSWORD: "Password must be at least 8 characters with upper, lower, and numbers.",
        Status.USERNAME_ALREADY_EXISTS: "This username is already taken.",
        Status.INVALID_USERNAME: "Username must be between 3 and 50 characters.",
        Status.UNAUTHORIZED: "Invalid username or password.",
        Status.DATABASE_ERROR: "Database error. Please try again later.",
    }
    return messages.get(status, "An unexpected error occurred.")
# SECURITY


def create_secure_password(password):
    # Create a highly secure, random 16-byte salt
    salt = os.urandom(16)

    # Hash the password by running SHA-256 exactly 600,000 times (the current global security standard)
    #    This makes it difficult for hackers to brute-force crack it.
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
