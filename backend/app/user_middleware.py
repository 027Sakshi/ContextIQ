from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.app.user_context import (
    set_current_user,
    clear_current_user,
)


class ContextIQUserMiddleware(BaseHTTPMiddleware):
    """
    Reads the currently logged-in ContextIQ user's email
    from the X-ContextIQ-User request header.

    Example header:

        X-ContextIQ-User: ucarding9@gmail.com

    The email is then stored in the backend request context
    and can be accessed by:

        get_current_user()
    """

    async def dispatch(
        self,
        request: Request,
        call_next,
    ):
        # ----------------------------------------------------
        # Read user email from frontend request
        # ----------------------------------------------------

        user_email = request.headers.get(
            "X-ContextIQ-User",
            "",
        ).strip().lower()

        # ----------------------------------------------------
        # Store user in backend context
        # ----------------------------------------------------

        set_current_user(
            user_email
        )

        try:

            # ------------------------------------------------
            # Continue request
            # ------------------------------------------------

            response = await call_next(
                request
            )

            return response

        finally:

            # ------------------------------------------------
            # Always clear user context after request
            # ------------------------------------------------

            clear_current_user()