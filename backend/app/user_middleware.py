from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.app.auth_session import verify_session_token
from backend.app.config import settings
from backend.app.user_context import clear_current_user, set_current_user


class ContextIQUserMiddleware(BaseHTTPMiddleware):
    """Resolve the ContextIQ user from a signed bearer session.

    X-ContextIQ-User remains available only when explicitly enabled for local
    development. Production identity must come from a signed session token.
    """

    async def dispatch(self, request: Request, call_next):
        user_email = ""
        authorization = request.headers.get("Authorization", "")

        if authorization.lower().startswith("bearer "):
            payload = verify_session_token(authorization[7:].strip())
            if payload:
                user_email = payload["email"]
                request.state.contextiq_user = payload

        if not user_email and settings.allow_dev_user_header:
            user_email = request.headers.get("X-ContextIQ-User", "")

        set_current_user(user_email)
        try:
            return await call_next(request)
        finally:
            clear_current_user()
