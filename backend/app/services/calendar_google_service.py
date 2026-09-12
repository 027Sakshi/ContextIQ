from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from backend.app.services.gmail_service import get_calendar_service

LOCAL_TZ = ZoneInfo("Asia/Kolkata")


def get_primary_calendar_events(days: int = 7):
    service = get_calendar_service()
    now = datetime.now(timezone.utc)
    end_time = now + timedelta(days=days)
    response = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat().replace("+00:00", "Z"),
        timeMax=end_time.isoformat().replace("+00:00", "Z"),
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return response.get("items", [])


def find_available_slot(duration_minutes: int = 30, days_ahead: int = 7):
    events = get_primary_calendar_events(days=days_ahead)
    busy_slots = []
    for event in events:
        start_value = (event.get("start") or {}).get("dateTime")
        end_value = (event.get("end") or {}).get("dateTime")
        if not start_value or not end_value:
            continue
        try:
            start = datetime.fromisoformat(start_value.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
            end = datetime.fromisoformat(end_value.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
            busy_slots.append((start, end))
        except ValueError:
            continue

    current = datetime.now(LOCAL_TZ)
    for day_offset in range(days_ahead):
        candidate = current + timedelta(days=day_offset)
        if candidate.weekday() >= 5:
            continue
        slot_start = candidate.replace(hour=10, minute=0, second=0, microsecond=0)
        if day_offset == 0 and slot_start < current:
            minutes = ((current.minute + 29) // 30) * 30
            slot_start = current.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=minutes)
            if slot_start < current:
                slot_start += timedelta(minutes=30)
        while slot_start.hour < 18:
            slot_end = slot_start + timedelta(minutes=duration_minutes)
            if slot_end.hour > 18 or (slot_end.hour == 18 and slot_end.minute > 0):
                break
            if not any(slot_start < busy_end and slot_end > busy_start for busy_start, busy_end in busy_slots):
                return {"date": slot_start.date().isoformat(), "start": slot_start.strftime("%H:%M"), "end": slot_end.strftime("%H:%M")}
            slot_start += timedelta(minutes=30)
    return None


def create_calendar_event(title: str, start_datetime: datetime, end_datetime: datetime, attendee_email: str | None = None):
    service = get_calendar_service()
    if start_datetime.tzinfo is None:
        start_datetime = start_datetime.replace(tzinfo=LOCAL_TZ)
    if end_datetime.tzinfo is None:
        end_datetime = end_datetime.replace(tzinfo=LOCAL_TZ)
    event = {
        "summary": title,
        "start": {"dateTime": start_datetime.isoformat(), "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end_datetime.isoformat(), "timeZone": "Asia/Kolkata"},
    }
    if attendee_email:
        event["attendees"] = [{"email": attendee_email}]
    return service.events().insert(calendarId="primary", body=event, sendUpdates="all" if attendee_email else "none").execute()
