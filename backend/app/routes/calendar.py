from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.models.calendar_event import CalendarEvent
from backend.app.user_context import require_current_user


# ============================================================
# CALENDAR ROUTER
# ============================================================

router = APIRouter(
    prefix="/calendar",
    tags=["Calendar"],
)


# ============================================================
# GET USER CALENDAR EVENTS
# ============================================================

@router.get("/")
def get_calendar_events(
    db: Session = Depends(get_db),
):
    """
    Return only calendar events related to the currently
    logged-in ContextIQ user.

    The current user is obtained from the backend request
    context created by the ContextIQ middleware.
    """

    try:

        # ----------------------------------------------------
        # Get logged-in user
        # ----------------------------------------------------

        user_email = require_current_user()

        # ----------------------------------------------------
        # Find events belonging to the current user
        #
        # owner:
        #     Used when the event owner is stored as email.
        #
        # attendees:
        #     Used when the logged-in user is an attendee.
        # ----------------------------------------------------

        events = (
            db.query(CalendarEvent)
            .filter(
                or_(
                    CalendarEvent.owner.ilike(
                        user_email
                    ),
                    CalendarEvent.attendees.ilike(
                        f"%{user_email}%"
                    )
                )
            )
            .order_by(
                CalendarEvent.event_date.asc()
            )
            .all()
        )

        # ----------------------------------------------------
        # Return structured response
        # ----------------------------------------------------

        return [
            {
                "id": event.id,

                "owner": event.owner,

                "title": event.title,

                "event_date": (
                    event.event_date.isoformat()
                    if event.event_date
                    else None
                ),

                "end_date": (
                    event.end_date.isoformat()
                    if event.end_date
                    else None
                ),

                "attendees": event.attendees,

                "status": event.status,
            }

            for event in events
        ]

    except ValueError as error:

        raise HTTPException(
            status_code=401,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not load calendar events: "
                f"{error}"
            ),
        )