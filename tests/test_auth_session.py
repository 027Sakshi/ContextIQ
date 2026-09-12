from backend.app.auth_session import create_session_token, verify_session_token


def test_signed_session_round_trip():
    token = create_session_token("User@Example.com", "User")
    payload = verify_session_token(token)
    assert payload == {"email": "user@example.com", "name": "User"}


def test_invalid_session_is_rejected():
    assert verify_session_token("not-a-valid-token") is None
