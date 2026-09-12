import pytest

from backend.app.user_context import (
    MissingUserContextError,
    clear_current_user,
    normalize_user_email,
    require_current_user,
    set_current_user,
)


def teardown_function():
    clear_current_user()


def test_normalize_user_email():
    assert normalize_user_email(
        "  USER@Example.COM "
    ) == "user@example.com"


def test_require_current_user():
    set_current_user("person@example.com")
    assert require_current_user() == "person@example.com"


def test_require_current_user_rejects_missing_context():
    clear_current_user()
    with pytest.raises(MissingUserContextError):
        require_current_user()
