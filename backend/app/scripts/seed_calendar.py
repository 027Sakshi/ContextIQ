from datetime import datetime, timedelta

from backend.app.database.connection import SessionLocal
from backend.app.models.calendar_event import CalendarEvent


def seed_calendar():

    db = SessionLocal()

    try:

        if db.query(CalendarEvent).count() > 0:

            print("Calendar data already exists.")
            return

        now = datetime.now()

        events = [

            CalendarEvent(
                owner="Rahul",
                title="Internal Sales Meeting",
                event_date=now + timedelta(days=1, hours=1),
                end_date=now + timedelta(days=1, hours=2),
                attendees="sales@contextiq-demo.com",
                status="scheduled"
            ),

            CalendarEvent(
                owner="Priya",
                title="Client Discussion",
                event_date=now + timedelta(days=2),
                end_date=now + timedelta(days=2, minutes=30),
                attendees="priya@xyzindustries.com",
                status="scheduled"
            ),

            CalendarEvent(
                owner="Arjun",
                title="Product Review",
                event_date=now + timedelta(days=3),
                end_date=now + timedelta(days=3, minutes=30),
                attendees="arjun@acmesolutions.com",
                status="scheduled"
            )
        ]

        db.add_all(events)

        db.commit()

        print("Mock calendar data inserted successfully!")

    except Exception as error:

        db.rollback()

        print(f"Error inserting calendar data: {error}")

    finally:

        db.close()


if __name__ == "__main__":
    seed_calendar()