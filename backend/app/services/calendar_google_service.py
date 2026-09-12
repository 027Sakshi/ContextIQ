from datetime import datetime, timedelta

from backend.app.services.gmail_service import (
    get_calendar_service
)


def get_primary_calendar_events(
    days: int = 7
):
    """
    Get upcoming events from the user's primary
    Google Calendar.
    """

    service = get_calendar_service()

    now = datetime.utcnow()
    end_time = now + timedelta(
        days=days
    )

    response = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now.isoformat() + "Z",
            timeMax=end_time.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime"
        )
        .execute()
    )

    return response.get(
        "items",
        []
    )


def find_available_slot(
    duration_minutes: int = 30,
    days_ahead: int = 7
):
    """
    Find a simple available weekday slot.
    Working hours: 10:00 to 18:00.
    """

    events = get_primary_calendar_events(
        days=days_ahead
    )

    busy_slots = []

    for event in events:

        start = event.get(
            "start",
            {}
        )

        end = event.get(
            "end",
            {}
        )

        start_value = (
            start.get("dateTime")
        )

        end_value = (
            end.get("dateTime")
        )

        if not start_value or not end_value:
            continue

        try:

            start_time = datetime.fromisoformat(
                start_value.replace(
                    "Z",
                    "+00:00"
                )
            )

            end_time = datetime.fromisoformat(
                end_value.replace(
                    "Z",
                    "+00:00"
                )
            )

            busy_slots.append(
                (
                    start_time,
                    end_time
                )
            )

        except ValueError:
            continue

    current_date = datetime.now()

    for day_offset in range(
        days_ahead
    ):

        candidate_date = (
            current_date
            + timedelta(days=day_offset)
        )

        if candidate_date.weekday() >= 5:
            continue

        slot_start = candidate_date.replace(
            hour=10,
            minute=0,
            second=0,
            microsecond=0
        )

        while slot_start.hour < 18:

            slot_end = (
                slot_start
                + timedelta(
                    minutes=duration_minutes
                )
            )

            conflict = False

            for busy_start, busy_end in busy_slots:

                if (
                    slot_start < busy_end
                    and slot_end > busy_start
                ):
                    conflict = True
                    break

            if not conflict:

                return {
                    "date": slot_start.date().isoformat(),
                    "start": slot_start.strftime("%H:%M"),
                    "end": slot_end.strftime("%H:%M"),
                }

            slot_start = (
                slot_start
                + timedelta(minutes=30)
            )

    return None


def create_calendar_event(
    title: str,
    start_datetime: datetime,
    end_datetime: datetime,
    attendee_email: str | None = None
):
    """
    Create an event in the user's primary
    Google Calendar.
    """

    service = get_calendar_service()

    event = {
        "summary": title,
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
    }

    if attendee_email:

        event["attendees"] = [
            {
                "email": attendee_email
            }
        ]

    created_event = (
        service.events()
        .insert(
            calendarId="primary",
            body=event
        )
        .execute()
    )

    return created_event