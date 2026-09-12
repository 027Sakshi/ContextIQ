from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from google.oauth2.credentials import Credentials

from backend.app.config import DATA_DIR, settings
from backend.app.user_context import normalize_user_email

TOKEN_DIR = DATA_DIR / "google_tokens"
TOKEN_DIR.mkdir(parents=True, exist_ok=True)


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.session_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _token_path(user_email: str) -> Path:
    normalized = normalize_user_email(user_email)
    if not normalized:
        raise ValueError("A valid user email is required.")
    filename = hashlib.sha256(normalized.encode("utf-8")).hexdigest() + ".token"
    return TOKEN_DIR / filename


def save_google_credentials(user_email: str, credentials: Credentials) -> None:
    payload = credentials.to_json().encode("utf-8")
    encrypted = _fernet().encrypt(payload)
    _token_path(user_email).write_bytes(encrypted)


def load_google_credentials(user_email: str, scopes: list[str] | None = None) -> Credentials | None:
    path = _token_path(user_email)
    if not path.exists():
        return None
    try:
        decrypted = _fernet().decrypt(path.read_bytes())
        info = json.loads(decrypted.decode("utf-8"))
        return Credentials.from_authorized_user_info(info, scopes=scopes)
    except (InvalidToken, ValueError, json.JSONDecodeError, OSError):
        return None


def delete_google_credentials(user_email: str) -> None:
    path = _token_path(user_email)
    if path.exists():
        path.unlink()
