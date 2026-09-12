from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.models.calendar_event import CalendarEvent


def get_calendar_context(
    sender: str,
    body: str,
    db: Session
) -> dict:
    """
    Detect meeting-related requests and provide
    calendar context.
    """

    text = body.lower()

    # --------------------------------------------------
    # Detect meeting request
    # --------------------------------------------------

    meeting_requested = any(
        word in text
        for word in [
            "meeting",
            "demo",
            "call",
            "schedule",
            "discussion",
            "appointment"
        ]
    )

    if not meeting_requested:

        return {
            "meeting_requested": False,
            "available_slot": None,
            "existing_events": [],
            "calendar_action": None
        }

    # --------------------------------------------------
    # Current time
    # --------------------------------------------------

    now = datetime.now()

    # --------------------------------------------------
    # Get upcoming events
    # --------------------------------------------------

    events = (
        db.query(CalendarEvent)
        .filter(
            CalendarEvent.event_date >= now
        )
        .order_by(CalendarEvent.event_date)
        .all()
    )

    existing_events = []

    for event in events:

        existing_events.append({
            "owner": event.owner,
            "title": event.title,
            "start": event.event_date.isoformat(),
            "end": event.end_date.isoformat(),
            "status": event.status
        })

    # --------------------------------------------------
    # Prototype availability
    # --------------------------------------------------

    available_slot = {
        "date": (
            now + timedelta(days=1)
        ).strftime("%Y-%m-%d"),

        "start": "15:00",

        "end": "15:30"
    }

    return {
        "meeting_requested": True,

        "available_slot": available_slot,

        "existing_events": existing_events,

        "calendar_action": "suggest_meeting"
    }