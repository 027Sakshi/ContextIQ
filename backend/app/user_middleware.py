from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.app.config import settings
from backend.app.user_context import clear_current_user, set_current_user


class ContextIQUserMiddleware(BaseHTTPMiddleware):
    """Populate request user context for the current development auth flow.

    X-ContextIQ-User is intentionally a DEVELOPMENT bridge only. Milestone 2
    replaces it with verified Google authentication. Production deployments
    must not trust a caller-supplied identity header.
    """

    async def dispatch(self, request: Request, call_next):
        user_email = ""

        if settings.allow_dev_user_header:
            user_email = request.headers.get("X-ContextIQ-User", "")

        set_current_user(user_email)

        try:
            return await call_next(request)
        finally:
            clear_current_user()
