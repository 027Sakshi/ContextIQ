from contextvars import ContextVar


# ============================================================
# Current User Context
# ============================================================
#
# This stores the email address of the user making the
# current backend request.
#
# Example:
#     ucarding9@gmail.com
#
# The value is kept inside the current request context so
# different users do not accidentally share one global value.
# ============================================================

_current_user_email: ContextVar[str] = ContextVar(
    "current_user_email",
    default="",
)


# ============================================================
# Normalize Email
# ============================================================

def normalize_user_email(email: str | None) -> str:
    """
    Normalize a user email address.

    Examples:
        " UCarding9@GMAIL.COM "
        ->
        "ucarding9@gmail.com"
    """

    if not email:
        return ""

    return email.strip().lower()


# ============================================================
# Set Current User
# ============================================================

def set_current_user(email: str | None) -> str:
    """
    Store the current logged-in user's email.

    Returns:
        Normalized email address.
    """

    normalized_email = normalize_user_email(email)

    _current_user_email.set(
        normalized_email
    )

    return normalized_email


# ============================================================
# Get Current User
# ============================================================

def get_current_user() -> str:
    """
    Return the current logged-in user's email.
    """

    return _current_user_email.get()


# ============================================================
# Require Current User
# ============================================================

def require_current_user() -> str:
    """
    Return the current user email.

    Raises:
        ValueError if no user has been set.
    """

    email = get_current_user()

    if not email:
        raise ValueError(
            "No logged-in user is available for this backend request."
        )

    return email


# ============================================================
# Clear Current User
# ============================================================

def clear_current_user():
    """
    Clear the current backend user context.
    """

    _current_user_email.set("")