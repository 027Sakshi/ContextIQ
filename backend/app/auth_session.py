from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from backend.app.config import settings
from backend.app.user_context import normalize_user_email

_SALT = "contextiq-session-v1"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret, salt=_SALT)


def create_session_token(email: str, name: str = "") -> str:
    normalized = normalize_user_email(email)
    if not normalized:
        raise ValueError("A valid user email is required.")
    return _serializer().dumps({"email": normalized, "name": (name or "").strip()})


def verify_session_token(token: str) -> dict | None:
    if not token:
        return None
    try:
        payload = _serializer().loads(token, max_age=settings.session_ttl_seconds)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict):
        return None
    email = normalize_user_email(payload.get("email"))
    if not email:
        return None
    return {"email": email, "name": str(payload.get("name") or "").strip()}
