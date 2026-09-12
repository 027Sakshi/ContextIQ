import json
import os
import re
import secrets
from pathlib import Path

import streamlit as st
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from backend.app.auth_session import create_session_token
from backend.app.config import settings
from backend.app.services.google_token_store import save_google_credentials

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOOGLE_OAUTH_CLIENT_FILE = PROJECT_ROOT / "credentials" / "google_oauth_client.json"
GOOGLE_OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


def is_valid_email(email: str) -> bool:
    return bool(email and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


def _name_from_email(email: str) -> str:
    return email.split("@")[0].replace(".", " ").replace("_", " ").replace("-", " ").title()


def initialize_auth():
    defaults = {
        "logged_in": False,
        "user_email": "",
        "user_name": "",
        "contextiq_session_token": "",
        "google_oauth_state": "",
        "google_profile": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def login_user(email: str, name: str | None = None, *, issue_session: bool = True) -> bool:
    email = (email or "").strip().lower()
    if not is_valid_email(email):
        return False
    resolved_name = (name or _name_from_email(email)).strip()
    st.session_state.logged_in = True
    st.session_state.user_email = email
    st.session_state.user_name = resolved_name
    if issue_session:
        st.session_state.contextiq_session_token = create_session_token(email, resolved_name)
    return True


def logout_user():
    for key in [
        "logged_in", "user_email", "user_name", "contextiq_session_token",
        "google_oauth_state", "google_profile", "analysis", "page",
        "business_insights",
    ]:
        st.session_state.pop(key, None)
    initialize_auth()


def google_oauth_configured() -> bool:
    return GOOGLE_OAUTH_CLIENT_FILE.exists()


def _load_google_client_config() -> dict:
    with open(GOOGLE_OAUTH_CLIENT_FILE, "r", encoding="utf-8") as file:
        config = json.load(file)
    if "web" not in config:
        raise ValueError("Google OAuth client must be a Web application client.")
    return config


def _oauth_state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret, salt="contextiq-google-oauth-v1")


def _create_oauth_state() -> str:
    return _oauth_state_serializer().dumps({"nonce": secrets.token_urlsafe(18)})


def _verify_oauth_state(state: str) -> bool:
    try:
        payload = _oauth_state_serializer().loads(state, max_age=600)
        return isinstance(payload, dict) and bool(payload.get("nonce"))
    except (BadSignature, SignatureExpired):
        return False


def create_google_authorization_url() -> str:
    flow = Flow.from_client_secrets_file(
        str(GOOGLE_OAUTH_CLIENT_FILE), scopes=GOOGLE_OAUTH_SCOPES
    )
    flow.redirect_uri = settings.google_oauth_redirect_uri
    state = _create_oauth_state()
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent select_account",
        state=state,
    )
    return authorization_url


def handle_google_oauth_callback() -> bool:
    code = st.query_params.get("code")
    returned_state = st.query_params.get("state")
    if not code:
        return False

    if not returned_state or not _verify_oauth_state(str(returned_state)):
        st.error("Google sign-in validation failed or expired. Please try again.")
        return False

    try:
        flow = Flow.from_client_secrets_file(
            str(GOOGLE_OAUTH_CLIENT_FILE),
            scopes=GOOGLE_OAUTH_SCOPES,
            state=str(returned_state),
        )
        flow.redirect_uri = settings.google_oauth_redirect_uri
        flow.fetch_token(code=code)
        credentials = flow.credentials

        client_config = _load_google_client_config()["web"]
        token_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            audience=client_config["client_id"],
            clock_skew_in_seconds=10,
        )

        email = str(token_info.get("email") or "").strip().lower()
        name = str(token_info.get("name") or _name_from_email(email)).strip()
        if not is_valid_email(email):
            raise ValueError("Google did not return a valid email address.")
        if token_info.get("email_verified") is False:
            raise ValueError("Google account email is not verified.")

        save_google_credentials(email, credentials)
        login_user(email, name)
        st.session_state.google_profile = token_info
        st.session_state.google_oauth_state = ""
        try:
            st.query_params.clear()
        except Exception:
            pass
        return True
    except Exception as error:
        st.error(f"Google sign-in failed: {error}")
        return False


def show_login_page() -> bool:
    initialize_auth()
    if handle_google_oauth_callback():
        st.rerun()
    if st.session_state.logged_in:
        return True

    st.markdown("""
    <style>
    [data-testid="stSidebar"]{display:none}.block-container{max-width:1080px;padding-top:4rem}
    .ctx-login{padding:2.6rem;border:1px solid rgba(128,128,128,.2);border-radius:28px;
    background:linear-gradient(135deg,rgba(78,104,255,.16),rgba(0,184,170,.08));margin-bottom:1.3rem}
    .ctx-login h1{font-size:3.4rem;letter-spacing:-.05em;margin:.2rem 0}.ctx-login p{font-size:1.06rem;opacity:.72;max-width:720px}
    </style>
    <div class="ctx-login"><small>AI BUSINESS DECISION INTELLIGENCE</small><h1>ContextIQ</h1>
    <p>Connect your Google account once. ContextIQ securely links Gmail and Calendar to your private business workspace, then turns communication into evidence-backed decisions and actions.</p></div>
    """, unsafe_allow_html=True)

    left, right = st.columns([1.1, .9], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("## Sign in")
            st.caption("Use the Google account whose Gmail and Calendar you want ContextIQ to understand.")
            if google_oauth_configured():
                try:
                    st.link_button("Continue with Google", create_google_authorization_url(), use_container_width=True, type="primary")
                except Exception as error:
                    st.error(f"Google OAuth is not ready: {error}")
            else:
                st.warning("Google OAuth client is not configured yet.")
                st.caption("Add credentials/google_oauth_client.json (Web application OAuth client).")

            if settings.allow_dev_email_login:
                st.divider()
                st.caption("Local development fallback")
                email = st.text_input("Developer email", placeholder="you@example.com")
                if st.button("Continue in dev mode", use_container_width=True):
                    if login_user(email):
                        st.rerun()
                    st.error("Enter a valid email address.")
    with right:
        st.markdown("### One identity, one workspace")
        st.write("• Google identity verified at sign-in")
        st.write("• Gmail read access for intelligence")
        st.write("• Calendar event access for planning/actions")
        st.write("• Per-user encrypted refresh tokens")
        st.write("• Signed ContextIQ API session")
        st.info("ContextIQ never commits Google tokens or OAuth credentials to Git.")
    return False
