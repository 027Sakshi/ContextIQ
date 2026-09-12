from datetime import datetime, timedelta

from backend.app.config import settings
from backend.app.database.base import Base
from backend.app.database.connection import SessionLocal, engine
from backend.app.models.calendar_event import CalendarEvent
from backend.app.user_context import normalize_user_email


def seed_calendar(user_email: str | None = None) -> None:
    user_email = normalize_user_email(
        user_email or settings.demo_user_email
    )

    if not user_email:
        raise ValueError(
            "A demo user email is required to seed calendar data."
        )

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        existing_count = (
            db.query(CalendarEvent)
            .filter(CalendarEvent.owner == user_email)
            .count()
        )

        if existing_count > 0:
            print(f"Calendar data already exists for {user_email}.")
            return

        now = datetime.now()
        events = [
            CalendarEvent(owner=user_email, title="Internal Sales Meeting", event_date=now + timedelta(days=1, hours=1), end_date=now + timedelta(days=1, hours=2), attendees="sales@contextiq-demo.com", status="scheduled"),
            CalendarEvent(owner=user_email, title="Client Discussion", event_date=now + timedelta(days=2), end_date=now + timedelta(days=2, minutes=30), attendees="priya@xyzindustries.com", status="scheduled"),
            CalendarEvent(owner=user_email, title="Product Review", event_date=now + timedelta(days=3), end_date=now + timedelta(days=3, minutes=30), attendees="arjun@acmesolutions.com", status="scheduled"),
        ]

        db.add_all(events)
        db.commit()
        print(
            f"Mock calendar data inserted successfully for {user_email}."
        )

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_calendar()
