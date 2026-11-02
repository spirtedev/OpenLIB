from enum import IntEnum, auto


class Status(IntEnum):
    # General
    SUCCESS = 0

    # Users related errors
    USER_NOT_FOUND = auto()
    USERNAME_ALREADY_EXISTS = auto()
    INVALID_USERNAME = auto()
    INVALID_PASSWORD = auto()
    INVALID_ROLE = auto()
    INVALID_CREDENTIALS = auto()

    # Books related errors
    BOOK_NOT_FOUND = auto()
    BOOK_ALREADY_EXISTS = auto()
    INVALID_TITLE = auto()
    INVALID_AUTHOR_NAME = auto()
    INVALID_GENRE = auto()
    INVALID_BOOK_QUANTITY = auto()

    # Loans related errors
    LOAN_NOT_FOUND = auto()
    LOAN_ALREADY_EXISTS = auto()
    BOOK_ALREADY_RETURNED = auto()
    BOOK_OUT_OF_STOCK = auto()
    BOOK_ACTUALLY_LOANED = auto()
    INVALID_LOAN_DURATION = auto()
    INVALID_DUE_DATE = auto()
    MAX_LOANS_REACHED = auto()
    MAX_LOANS_EXCEEDED = auto()

    # Roles related errors
    UNAUTHORIZED = auto()
    FORBIDDEN = auto()

    # Database related errors
    DATABASE_ERROR = auto()
    INVALID_INPUT = auto()
    NOTHING_TO_EDIT = auto()
