from contextvars import ContextVar


class MissingUserContextError(ValueError):
    """Raised when a protected operation has no authenticated user context."""


_current_user_email: ContextVar[str] = ContextVar(
    "current_user_email",
    default="",
)


def normalize_user_email(email: str | None) -> str:
    if not email:
        return ""
    return email.strip().lower()


def set_current_user(email: str | None) -> str:
    normalized_email = normalize_user_email(email)
    _current_user_email.set(normalized_email)
    return normalized_email


def get_current_user() -> str:
    return _current_user_email.get()


def require_current_user() -> str:
    email = get_current_user()
    if not email:
        raise MissingUserContextError(
            "No authenticated ContextIQ user is available for this request."
        )
    return email


def clear_current_user() -> None:
    _current_user_email.set("")
