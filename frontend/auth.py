import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode

import streamlit as st
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow


# ==========================================================
# PATHS / GOOGLE OAUTH CONFIG
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GOOGLE_OAUTH_CLIENT_FILE = (
    PROJECT_ROOT / "credentials" / "google_oauth_client.json"
)

GOOGLE_OAUTH_REDIRECT_URI = os.getenv(
    "GOOGLE_OAUTH_REDIRECT_URI",
    "http://localhost:8501",
).strip()

GOOGLE_OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


# ==========================================================
# BASIC HELPERS
# ==========================================================

def is_valid_email(email: str) -> bool:
    email = (email or "").strip()

    if not email:
        return False

    return (
        re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            email,
        )
        is not None
    )


def name_from_email(email: str) -> str:
    username = (
        email.split("@", 1)[0]
        .replace(".", " ")
        .replace("_", " ")
        .replace("-", " ")
    )

    return username.title()


# ==========================================================
# SESSION INITIALIZATION
# ==========================================================

def initialize_auth():
    defaults = {
        "logged_in": False,
        "user_email": "",
        "user_name": "",
        "google_oauth_state": "",
        "google_profile": {},
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ==========================================================
# DIRECT EMAIL LOGIN
# ==========================================================

def login_user(
    email: str,
    name: str | None = None,
) -> bool:
    """
    ContextIQ local/demo login.

    Any syntactically valid email address can be used.
    This is intentionally separate from Google OAuth.
    """

    normalized = (
        email or ""
    ).strip().lower()

    if not is_valid_email(
        normalized
    ):
        return False

    st.session_state[
        "logged_in"
    ] = True

    st.session_state[
        "user_email"
    ] = normalized

    st.session_state[
        "user_name"
    ] = (
        name.strip()
        if name and name.strip()
        else name_from_email(
            normalized
        )
    )

    # Clear stale page/data from a previous user.
    st.session_state[
        "page"
    ] = "Dashboard"

    st.session_state[
        "analysis"
    ] = None

    st.session_state[
        "business_insights"
    ] = {}

    return True


def logout_user():
    clear_keys = [
        "logged_in",
        "user_email",
        "user_name",
        "google_oauth_state",
        "google_profile",
        "analysis",
        "page",
        "business_insights",
    ]

    for key in clear_keys:
        st.session_state.pop(
            key,
            None,
        )

    initialize_auth()


# ==========================================================
# GOOGLE OAUTH
# ==========================================================

def google_oauth_configured() -> bool:
    return (
        GOOGLE_OAUTH_CLIENT_FILE.exists()
    )


def create_google_authorization_url() -> str:
    flow = Flow.from_client_secrets_file(
        str(
            GOOGLE_OAUTH_CLIENT_FILE
        ),
        scopes=GOOGLE_OAUTH_SCOPES,
    )

    flow.redirect_uri = (
        GOOGLE_OAUTH_REDIRECT_URI
    )

    authorization_url, state = (
        flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="select_account",
        )
    )

    st.session_state[
        "google_oauth_state"
    ] = state

    return authorization_url


def handle_google_callback() -> bool:
    code = st.query_params.get(
        "code"
    )

    returned_state = st.query_params.get(
        "state"
    )

    if not code:
        return False

    expected_state = (
        st.session_state.get(
            "google_oauth_state",
            "",
        )
    )

    if not expected_state:
        st.error(
            "Google sign-in session expired. "
            "Please click Continue with Google again."
        )
        return False

    if returned_state != expected_state:
        st.error(
            "Google sign-in verification failed. "
            "Please try again."
        )
        return False

    try:
        flow = Flow.from_client_secrets_file(
            str(
                GOOGLE_OAUTH_CLIENT_FILE
            ),
            scopes=GOOGLE_OAUTH_SCOPES,
            state=expected_state,
        )

        flow.redirect_uri = (
            GOOGLE_OAUTH_REDIRECT_URI
        )

        authorization_response = (
            GOOGLE_OAUTH_REDIRECT_URI
            + "?"
            + urlencode(
                {
                    "code": code,
                    "state": returned_state,
                }
            )
        )

        flow.fetch_token(
            authorization_response=authorization_response
        )

        credentials = flow.credentials

        token_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            clock_skew_in_seconds=10,
        )

        email = (
            token_info.get(
                "email",
                "",
            )
            .strip()
            .lower()
        )

        name = (
            token_info.get(
                "name"
            )
            or name_from_email(
                email
            )
        )

        if not is_valid_email(
            email
        ):
            raise ValueError(
                "Google did not return a valid account email."
            )

        login_user(
            email=email,
            name=name,
        )

        st.session_state[
            "google_profile"
        ] = token_info

        st.query_params.clear()

        return True

    except Exception as error:
        st.error(
            "Google sign-in failed: "
            f"{error}"
        )
        return False


# ==========================================================
# LOGIN PAGE
# ==========================================================

def show_login_page() -> bool:
    initialize_auth()

    if handle_google_callback():
        st.rerun()

    if st.session_state.get(
        "logged_in",
        False,
    ):
        return True

    # Hide sidebar while logged out.
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }

        .block-container {
            max-width: 1160px;
            padding-top: 3rem;
            padding-bottom: 3rem;
        }

        .login-hero {
            padding: 2.2rem 2.4rem;
            border-radius: 28px;
            border: 1px solid rgba(128,128,128,.22);
            background:
                linear-gradient(
                    135deg,
                    rgba(79,107,255,.18),
                    rgba(0,188,172,.10)
                );
            margin-bottom: 1.4rem;
        }

        .login-eyebrow {
            font-size: .76rem;
            font-weight: 800;
            letter-spacing: .15em;
            text-transform: uppercase;
            opacity: .62;
        }

        .login-brand {
            font-size: 3.35rem;
            line-height: 1;
            font-weight: 900;
            letter-spacing: -.055em;
            margin-top: .35rem;
        }

        .login-tagline {
            margin-top: .65rem;
            font-size: 1.05rem;
            line-height: 1.55;
            opacity: .72;
            max-width: 760px;
        }

        .feature-card {
            padding: 1rem 1.05rem;
            border: 1px solid rgba(128,128,128,.18);
            border-radius: 17px;
            margin-bottom: .75rem;
        }

        .feature-title {
            font-weight: 800;
            margin-bottom: .15rem;
        }

        .feature-text {
            opacity: .68;
            font-size: .87rem;
            line-height: 1.45;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="login-hero">
            <div class="login-eyebrow">
                AI Business Email Intelligence
            </div>
            <div class="login-brand">
                ContextIQ
            </div>
            <div class="login-tagline">
                Turn inbox noise into business intelligence.
                Understand the email, connect its business context,
                predict consequence, and act with confidence.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(
        [1.15, 0.85],
        gap="large",
    )

    with left:
        with st.container(
            border=True
        ):
            st.markdown(
                "## Welcome back"
            )

            st.caption(
                "Sign in to open your ContextIQ command center."
            )

            # --------------------------------------------------
            # REAL GOOGLE LOGIN
            # --------------------------------------------------

            if google_oauth_configured():
                try:
                    google_url = (
                        create_google_authorization_url()
                    )

                    st.link_button(
                        "🔵 Continue with Google",
                        google_url,
                        use_container_width=True,
                    )

                    st.caption(
                        "Google will let you choose the account "
                        "currently signed into this browser."
                    )

                except Exception as error:
                    st.error(
                        f"Google OAuth configuration error: {error}"
                    )

            else:
                st.info(
                    "Google sign-in is not configured yet. "
                    "Email sign-in below works independently."
                )

            st.markdown(
                """
                <div style="
                    text-align:center;
                    opacity:.5;
                    margin:1.1rem 0;
                    font-size:.9rem;
                ">
                    OR
                </div>
                """,
                unsafe_allow_html=True,
            )

            # --------------------------------------------------
            # DIRECT EMAIL LOGIN
            # --------------------------------------------------

            with st.form(
                "direct_email_login_form",
                clear_on_submit=False,
            ):
                email = st.text_input(
                    "Work email",
                    placeholder="you@company.com",
                    key="direct_login_email",
                )

                submit = st.form_submit_button(
                    "Continue with Email →",
                    use_container_width=True,
                    type="primary",
                )

            if submit:
                normalized = (
                    email or ""
                ).strip().lower()

                if not normalized:
                    st.error(
                        "Please enter your email address."
                    )

                elif not is_valid_email(
                    normalized
                ):
                    st.error(
                        "Please enter a valid email address, "
                        "for example name@company.com."
                    )

                else:
                    login_user(
                        normalized
                    )

                    # Force Streamlit to run the main app
                    # immediately after successful login.
                    st.rerun()

            st.caption(
                "Direct email login is available for the ContextIQ prototype."
            )

    with right:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-title">
                    🔗 Business Context Graph
                </div>
                <div class="feature-text">
                    Connect email, people, company, CRM,
                    previous conversations, documents, and meetings.
                </div>
            </div>

            <div class="feature-card">
                <div class="feature-title">
                    ⚠️ Consequence Intelligence
                </div>
                <div class="feature-text">
                    Understand what the business could lose or delay
                    when an important email is ignored.
                </div>
            </div>

            <div class="feature-card">
                <div class="feature-title">
                    🤖 Risk-Aware Actions
                </div>
                <div class="feature-text">
                    Recommend, approve, execute, and track
                    business actions safely.
                </div>
            </div>

            <div class="feature-card">
                <div class="feature-title">
                    📊 Explainable Decisions
                </div>
                <div class="feature-text">
                    Show why ContextIQ prioritized an email,
                    identified risk, and recommended an action.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return False
