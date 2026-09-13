
import secrets
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

import hmac
import json
import os
import re
from pathlib import Path

import streamlit as st
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

from backend.app.auth_session import create_session_token
from backend.app.config import settings
from backend.app.services.google_token_store import (
    load_google_credentials,
    save_google_credentials,
)
from frontend.theme import apply_login_theme

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
        "ctx_light_mode": False,
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
        "logged_in",
        "user_email",
        "user_name",
        "contextiq_session_token",
        "google_oauth_state",
        "google_profile",
        "analysis",
        "page",
        "business_insights",
        "morning_brief",
    ]:
        st.session_state.pop(key, None)
    initialize_auth()


def _environment_google_config() -> dict | None:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None

    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_oauth_redirect_uri],
        }
    }


def _load_google_client_config() -> dict:
    if GOOGLE_OAUTH_CLIENT_FILE.exists():
        with open(GOOGLE_OAUTH_CLIENT_FILE, "r", encoding="utf-8") as file:
            config = json.load(file)

        if "web" not in config:
            raise ValueError("Google OAuth client must be a Web application client.")
        return config

    config = _environment_google_config()
    if config:
        return config

    raise FileNotFoundError(
        "Google OAuth is not configured. Add credentials/google_oauth_client.json "
        "or set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
    )


def google_oauth_configured() -> bool:
    try:
        _load_google_client_config()
        return True
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def google_workspace_connected(user_email: str | None = None) -> bool:
    email = (user_email or st.session_state.get("user_email", "") or "").strip().lower()
    if not email:
        return False

    try:
        credentials = load_google_credentials(email, scopes=GOOGLE_OAUTH_SCOPES)
        return bool(credentials and (credentials.valid or credentials.refresh_token))
    except Exception:
        return False



GOOGLE_OAUTH_STATE_SALT = "contextiq-google-oauth-state-v1"
GOOGLE_OAUTH_STATE_TTL_SECONDS = 900


def _google_oauth_state_serializer() -> URLSafeTimedSerializer:
    secret = os.getenv(
        "CONTEXTIQ_SESSION_SECRET",
        "",
    ).strip()

    if not secret:
        raise RuntimeError(
            "CONTEXTIQ_SESSION_SECRET is required "
            "for Google OAuth."
        )

    return URLSafeTimedSerializer(
        secret_key=secret,
        salt=GOOGLE_OAUTH_STATE_SALT,
    )


def _create_google_oauth_state() -> str:
    """
    Create a signed state value that survives the external Google
    redirect without depending on Streamlit session_state.
    """
    return _google_oauth_state_serializer().dumps(
        {
            "nonce": secrets.token_urlsafe(24),
            "provider": "google",
        }
    )


def _validate_google_oauth_state(
    state: str,
) -> bool:
    if not state:
        return False

    try:
        payload = _google_oauth_state_serializer().loads(
            state,
            max_age=GOOGLE_OAUTH_STATE_TTL_SECONDS,
        )
    except (
        BadSignature,
        SignatureExpired,
        TypeError,
        ValueError,
    ):
        return False

    return (
        isinstance(payload, dict)
        and payload.get("provider") == "google"
        and bool(payload.get("nonce"))
    )


def create_google_authorization_url() -> str:
    state = _create_google_oauth_state()

    flow = Flow.from_client_config(
        _load_google_client_config(),
        scopes=GOOGLE_OAUTH_SCOPES,
        state=state,
    )

    flow.redirect_uri = settings.google_oauth_redirect_uri

    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent select_account",
    )

    return authorization_url


def handle_google_oauth_callback() -> bool:
    code = st.query_params.get("code")
    returned_state = st.query_params.get("state")

    if not code:
        return False

    expected_state = str(returned_state or "")

    if not _validate_google_oauth_state(
        expected_state
    ):
        st.error(
            "Google sign-in validation failed. "
            "Start the Google sign-in again."
        )
        return False

    try:
        flow = Flow.from_client_config(
            _load_google_client_config(),
            scopes=GOOGLE_OAUTH_SCOPES,
            state=expected_state,
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

    apply_login_theme("light" if st.session_state.get("ctx_light_mode") else "dark")

    left, right = st.columns([1.18, .82], gap="large")

    with left:
        st.markdown(
            """
            <div class="ctx-login-wordmark"><span class="ctx-logo">CQ</span> ContextIQ</div>
            <div class="ctx-login-heading">Know what needs attention before the inbox gets noisy.</div>
            <div class="ctx-login-copy">
                A private operating workspace that connects communication, calendar and business context,
                then turns it into evidence-backed priorities and controlled actions.
            </div>

            <div class="ctx-proof">
                <div class="ctx-proof-row">
                    <div class="ctx-proof-index">01</div>
                    <div class="ctx-proof-text">
                        <strong>See business impact first</strong>
                        <span>Rank communication by customer, revenue, urgency and process consequence.</span>
                    </div>
                </div>
                <div class="ctx-proof-row">
                    <div class="ctx-proof-index">02</div>
                    <div class="ctx-proof-text">
                        <strong>Trace every recommendation</strong>
                        <span>Ground decisions in email, CRM, documents, commitments and calendar evidence.</span>
                    </div>
                </div>
                <div class="ctx-proof-row">
                    <div class="ctx-proof-index">03</div>
                    <div class="ctx-proof-text">
                        <strong>Stay in control</strong>
                        <span>ContextIQ prepares drafts and actions; nothing executes without approval.</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        with st.container(border=True):
            st.markdown(
                '<div class="ctx-login-card-title">Sign in to your workspace</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="ctx-login-card-copy">'
                'Use the Google account whose Gmail and Calendar you want ContextIQ to understand.'
                '</div>',
                unsafe_allow_html=True,
            )

            if google_oauth_configured():
                try:
                    st.link_button(
                        "Continue with Google",
                        create_google_authorization_url(),
                        use_container_width=True,
                        type="primary",
                    )
                except Exception as error:
                    st.error(f"Google sign-in is not ready: {error}")
            else:
                st.button(
                    "Continue with Google",
                    use_container_width=True,
                    disabled=True,
                )
                st.warning("Google OAuth setup is required once on this laptop.")
                st.caption(
                    "Add credentials/google_oauth_client.json, or set "
                    "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."
                )

            st.markdown(
                '<div class="ctx-oauth-note">'
                'ContextIQ requests Google identity, Gmail read access and Calendar event access. '
                'Credentials stay encrypted per user outside Git.'
                '</div>',
                unsafe_allow_html=True,
            )

            if settings.allow_dev_email_login:
                with st.expander("Developer access"):
                    email = st.text_input(
                        "Developer email",
                        placeholder="you@example.com",
                        label_visibility="collapsed",
                    )
                    if st.button("Continue in dev mode", use_container_width=True):
                        if login_user(email):
                            st.rerun()
                        else:
                            st.error("Enter a valid email address.")

            st.toggle("Light mode", key="ctx_light_mode")

    # Production fallback: direct ContextIQ workspace sign-in.
    # This creates the same ContextIQ session as Google sign-in, while Google
    # Workspace APIs still require a real OAuth connection for that email.
    direct_login_enabled = (
        os.getenv("ALLOW_DIRECT_EMAIL_LOGIN", "true").strip().lower()
        in {"1", "true", "yes", "on"}
    )

    if direct_login_enabled:
        st.markdown(
            '<div style="display:flex;align-items:center;gap:12px;margin:12px 0;color:#8b93a7;font-size:12px;">'
            '<span style="height:1px;background:rgba(128,128,128,.22);flex:1"></span>'
            '<span>or</span>'
            '<span style="height:1px;background:rgba(128,128,128,.22);flex:1"></span>'
            '</div>',
            unsafe_allow_html=True,
        )

        with st.form("contextiq_direct_login_form", clear_on_submit=False):
            direct_email = st.text_input(
                "Work email",
                placeholder="you@company.com",
                key="contextiq_direct_email",
            )
            required_code = os.getenv("CONTEXTIQ_DIRECT_LOGIN_CODE", "").strip()
            direct_code = ""
            if required_code:
                direct_code = st.text_input(
                    "Workspace access code",
                    type="password",
                    key="contextiq_direct_access_code",
                )
            direct_submit = st.form_submit_button(
                "Continue with email",
                use_container_width=True,
            )

        if direct_submit:
            normalized_email = direct_email.strip().lower()
            valid_email = (
                "@" in normalized_email
                and "." in normalized_email.rsplit("@", 1)[-1]
            )
            if not valid_email:
                st.error("Enter a valid work email.")
            elif required_code and not hmac.compare_digest(
                direct_code.strip(),
                required_code,
            ):
                st.error("Invalid workspace access code.")
            else:
                st.session_state["user_email"] = normalized_email
                st.session_state["user_name"] = (
                    normalized_email.split("@", 1)[0]
                    .replace(".", " ")
                    .replace("_", " ")
                    .replace("-", " ")
                    .title()
                )
                st.session_state["contextiq_session_token"] = (
                    create_session_token(normalized_email)
                )
                st.session_state["authenticated"] = True
                st.session_state["logged_in"] = True
                st.session_state["auth_source"] = "direct"
                st.session_state["google_authenticated"] = False
                st.rerun()

    return False
