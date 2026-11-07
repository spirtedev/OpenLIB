"""
Who may do what. This is the ONE place where the permission rules live.

Every page and every button callback asks has_permission() (through
gui_helpers.user_is_allowed) before doing something restricted, so a Member
can never reach Librarian/Admin features even if a button were somehow shown.
"""

# action name -> list of roles that are allowed to do it
PERMISSIONS = {
    "view_books": ["Member", "Librarian", "Admin"],
    "manage_own_account": ["Member", "Librarian", "Admin"],
    "borrow_books": ["Member"],            # only Members borrow
    "view_my_loans": ["Member"],           # personal loans + history: Members only
    "manage_books": ["Librarian", "Admin"],  # add / edit / delete books
    "view_members": ["Librarian", "Admin"],
    "view_member_loans": ["Librarian", "Admin"],
    "manage_users": ["Admin"],             # full users list, create/edit/delete users
}


def has_permission(role, action):
    """
    Tells if a role may do an action.
    Parameters: role (text, e.g. "Member"), action (a key of PERMISSIONS).
    Returns True or False. Unknown actions are always refused.
    """
    allowed_roles = PERMISSIONS.get(action, [])
    return role in allowed_roles
