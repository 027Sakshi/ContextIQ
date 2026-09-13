from pathlib import Path


def test_direct_login_is_present_in_release():
    auth = Path("frontend/auth.py").read_text(encoding="utf-8")
    assert "ALLOW_DIRECT_EMAIL_LOGIN" in auth
    assert "Continue with email" in auth
    assert "create_session_token" in auth


def test_cloud_entrypoint_bridges_direct_login_settings():
    entry = Path("streamlit_app.py").read_text(encoding="utf-8")
    assert "ALLOW_DIRECT_EMAIL_LOGIN" in entry
    assert "CONTEXTIQ_DIRECT_LOGIN_CODE" in entry
