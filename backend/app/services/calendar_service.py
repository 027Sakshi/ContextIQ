from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.models.calendar_event import CalendarEvent
from backend.app.user_context import require_current_user


def get_calendar_context(
    sender: str,
    body: str,
    db: Session,
) -> dict:
    text = (body or "").lower()

    meeting_requested = any(
        word in text
        for word in [
            "meeting",
            "demo",
            "call",
            "schedule",
            "discussion",
            "appointment",
        ]
    )

    if not meeting_requested:
        return {
            "meeting_requested": False,
            "available_slot": None,
            "existing_events": [],
            "calendar_action": None,
        }

    user_email = require_current_user()
    now = datetime.now()

    events = (
        db.query(CalendarEvent)
        .filter(
            CalendarEvent.event_date >= now,
            or_(
                CalendarEvent.owner.ilike(user_email),
                CalendarEvent.attendees.ilike(f"%{user_email}%"),
            ),
        )
        .order_by(CalendarEvent.event_date)
        .all()
    )

    existing_events = [
        {
            "owner": event.owner,
            "title": event.title,
            "start": event.event_date.isoformat(),
            "end": event.end_date.isoformat(),
            "status": event.status,
        }
        for event in events
    ]

    available_slot = {
        "date": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
        "start": "15:00",
        "end": "15:30",
    }

    return {
        "meeting_requested": True,
        "available_slot": available_slot,
        "existing_events": existing_events,
        "calendar_action": "suggest_meeting",
    }
