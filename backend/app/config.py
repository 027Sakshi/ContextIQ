from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(PROJECT_ROOT / ".env", override=False)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _default_database_url() -> str:
    db_path = (DATA_DIR / "contextiq.db").resolve().as_posix()
    return f"sqlite:///{db_path}"


_APP_ENV = os.getenv("CONTEXTIQ_ENV", "development").strip().lower()


@dataclass(frozen=True)
class Settings:
    app_env: str = _APP_ENV
    database_url: str = os.getenv("DATABASE_URL", _default_database_url()).strip()
    api_url: str = os.getenv("CONTEXTIQ_API_URL", "http://127.0.0.1:8000").rstrip("/")
    allow_dev_user_header: bool = _env_bool("ALLOW_DEV_USER_HEADER", False)
    allow_dev_email_login: bool = _env_bool("ALLOW_DEV_EMAIL_LOGIN", _APP_ENV != "production")
    session_secret: str = os.getenv("CONTEXTIQ_SESSION_SECRET", "contextiq-dev-only-change-me").strip()
    session_ttl_seconds: int = int(os.getenv("CONTEXTIQ_SESSION_TTL_SECONDS", "43200"))
    google_oauth_redirect_uri: str = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8501").strip()
    demo_user_email: str = os.getenv("DEMO_USER_EMAIL", "demo@contextiq.local").strip().lower()
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()
