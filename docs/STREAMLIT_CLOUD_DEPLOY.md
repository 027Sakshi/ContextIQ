# Streamlit Community Cloud deployment

ContextIQ uses `streamlit_app.py` as its cloud entrypoint. The entrypoint bridges
Streamlit secrets into ContextIQ's environment and starts the FastAPI backend on
`127.0.0.1:8000` inside the same Streamlit container.

## Deployment settings

- Repository: `027Sakshi/ContextIQ`
- Branch: `main`
- Entrypoint: `streamlit_app.py`
- Python: `3.11`
- Developer email login: disabled for submission/demo

Choose a custom Streamlit subdomain first. Use the exact resulting app URL as
`GOOGLE_OAUTH_REDIRECT_URI` and add the exact same URI to the Google Cloud Web
OAuth client's Authorized redirect URIs.

## Streamlit Cloud secrets

Paste these in Advanced settings -> Secrets. Never commit real values.

```toml
GEMINI_API_KEY = "..."
GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_THINKING_LEVEL = "low"
GOOGLE_CLIENT_ID = "...apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "..."
GOOGLE_OAUTH_REDIRECT_URI = "https://YOUR-SUBDOMAIN.streamlit.app"
CONTEXTIQ_SESSION_SECRET = "A-LONG-RANDOM-SECRET"
ALLOW_DEV_EMAIL_LOGIN = "false"
DATABASE_URL = "sqlite:///data/contextiq.db"
# HF_TOKEN = "hf_..." # optional
```

Keep the Google OAuth consent screen in Testing for the hackathon and add every
demo Google account as a test user.

## Release checks

```powershell
python -m compileall -q backend frontend ai tests scripts streamlit_app.py
python -m pytest -q
python scripts/check_gemini.py
python scripts/check_cloud_ready.py
.\scripts\check_release.ps1
```

## Demo caveat

Community Cloud can restart or hibernate the app. SQLite data and encrypted
Google token files are local to the running deployment, so a restart can require
a fresh Google sign-in and Gmail sync. For the hackathon demo, sign in and sync
before judging. A long-lived production deployment should use persistent managed
storage for database/token state.

## Two supported sign-in paths

ContextIQ intentionally supports both:

1. **Continue with Google** — creates the ContextIQ session and connects Gmail/Calendar in one flow.
2. **Continue with email** — opens the same ContextIQ workspace directly. If the same email already has a stored Google token, Workspace features are available immediately; otherwise use **Connect Google** inside the app before Gmail/Calendar actions.

Cloud secrets:

```toml
ALLOW_DIRECT_EMAIL_LOGIN = "true"
# Recommended for an internet deployment. Leave empty only for a controlled private demo.
CONTEXTIQ_DIRECT_LOGIN_CODE = "YOUR-PRIVATE-WORKSPACE-CODE"
```

Direct sign-in does not fake Google authorization. Google-dependent actions always require a real OAuth token.
