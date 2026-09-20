import re
from email.utils import parseaddr

from sqlalchemy.orm import Session

from backend.app.models.contact import Contact
from backend.app.models.company import Company
from backend.app.models.crm_record import CRMRecord
from backend.app.models.opportunity import Opportunity
from backend.app.models.calendar_event import CalendarEvent
from backend.app.user_context import require_current_user


# ==========================================================
# HELPERS
# ==========================================================

def normalize_email_address(sender: str) -> str:
    """
    Convert:
        Rahul Sharma <rahul@example.com>
    into:
        rahul@example.com
    """
    if not sender:
        return ""

    _, parsed_email = parseaddr(sender)

    if parsed_email:
        return parsed_email.strip().lower()

    match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        sender
    )

    if match:
        return match.group(0).strip().lower()

    return sender.strip().lower()


def extract_sender_name(sender: str) -> str:
    """
    Extract a readable sender name.
    """
    if not sender:
        return "Unknown"

    name, email_address = parseaddr(sender)

    if name:
        return name.strip()

    if email_address:
        local_part = email_address.split("@")[0]

        local_part = re.sub(
            r"[._-]+",
            " ",
            local_part
        )

        return local_part.title()

    return "Unknown"


def find_company_name_from_body(body: str) -> str | None:
    """
    Look for a simple company mention in the email body.

    Examples:
        ABC Technologies
        XYZ Industries
    """
    if not body:
        return None

    patterns = [
        r"\b([A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,3})\s+(?:Technologies|Industries|Corporation|Corp|Solutions|Systems|Ltd|Limited|Inc)\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            body
        )

        if match:
            return match.group(0).strip()

    # Common demo company explicitly mentioned in the email
    if "ABC Technologies" in body:
        return "ABC Technologies"

    if "XYZ Industries" in body:
        return "XYZ Industries"

    return None


# ==========================================================
# BUSINESS CONTEXT
# ==========================================================

def build_business_context(
    sender: str,
    body: str,
    db: Session
) -> dict:
    """
    Build the Business Context Graph for an email.

    The sender coming from Gmail may look like:
        Bhavya Thakkar <thakkar.bhavya2303@gmail.com>

    The database normally stores only:
        thakkar.bhavya2303@gmail.com

    Therefore the email address is normalized before lookup.

    All user-owned business context is restricted to the
    currently logged-in ContextIQ user.
    """

    # ======================================================
    # CURRENT USER
    # ======================================================

    user_email = require_current_user()

    # ======================================================
    # SENDER
    # ======================================================

    sender_email = normalize_email_address(
        sender
    )

    sender_name = extract_sender_name(
        sender
    )

    body_company = find_company_name_from_body(
        body
    )

    # ======================================================
    # CONTACT LOOKUP
    # ======================================================

    contact = None

    if sender_email:
        contact = (
            db.query(Contact)
            .filter(
                Contact.email.ilike(
                    sender_email
                ),
                Contact.user_email == user_email
            )
            .first()
        )

    # ======================================================
    # COMPANY DETERMINATION
    # ======================================================

    company_name = None

    # The current email is stronger evidence than a historical
    # Contact.company value. This allows one tester Gmail account
    # to represent different demo companies without cross-linking.
    if body_company:
        company_name = body_company

    if (
        not company_name
        and contact
        and contact.company
    ):
        company_name = (
            contact.company.strip()
        )

    # ======================================================
    # COMPANY LOOKUP
    # ======================================================

    company = None

    if company_name:
        company = (
            db.query(Company)
            .filter(
                Company.name.ilike(
                    company_name
                ),
                Company.user_email == user_email
            )
            .order_by(
                Company.id.desc()
            )
            .first()
        )

        if company:
            company_name = company.name

    # ======================================================
    # CRM LOOKUP
    # ======================================================

    crm = None

    if company_name:
        crm = (
            db.query(CRMRecord)
            .filter(
                CRMRecord.company_name.ilike(
                    company_name
                ),
                CRMRecord.user_email == user_email
            )
            .order_by(
                CRMRecord.id.desc()
            )
            .first()
        )

    # ======================================================
    # OPPORTUNITY LOOKUP
    # ======================================================

    opportunity = None

    if company_name:
        opportunity = (
            db.query(Opportunity)
            .filter(
                Opportunity.company_name.ilike(
                    company_name
                ),
                Opportunity.user_email == user_email
            )
            .order_by(
                Opportunity.id.desc()
            )
            .first()
        )

    # ======================================================
    # EMAIL HISTORY
    # ======================================================

    # Import locally to avoid circular imports.
    from backend.app.models.email import Email

    history_count = 0

    if sender_email:
        history_count = (
            db.query(Email)
            .filter(
                Email.sender.ilike(
                    f"%{sender_email}%"
                ),
                Email.user_email == user_email
            )
            .count()
        )

    # ======================================================
    # CALENDAR
    # ======================================================

    calendar_events = []

    if sender_email:
        calendar_events = (
            db.query(CalendarEvent)
            .filter(
                CalendarEvent.attendees.ilike(
                    f"%{sender_email}%"
                ),
                (
                    CalendarEvent.owner.ilike(
                        user_email
                    )
                    |
                    CalendarEvent.attendees.ilike(
                        f"%{user_email}%"
                    )
                )
            )
            .order_by(
                CalendarEvent.event_date.desc()
            )
            .limit(10)
            .all()
        )

    # ======================================================
    # CONTACT RESULT
    # ======================================================

    contact_result = None

    if contact:
        contact_result = {
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "company": contact.company,
        }

    else:
        # We can still expose sender identity even when
        # there is no pre-existing Contact record.
        if sender_email:
            contact_result = {
                "id": None,
                "name": sender_name,
                "email": sender_email,
                "company": company_name,
            }

    # ======================================================
    # CRM RESULT
    # ======================================================

    crm_result = None

    if crm:
        crm_result = {
            "id": crm.id,
            "company_name": crm.company_name,
            "contact_name": crm.contact_name,
            "deal_value": crm.deal_value,
            "stage": crm.stage,
            "status": crm.status,
        }

    # ======================================================
    # OPPORTUNITY RESULT
    # ======================================================

    opportunity_result = None

    if opportunity:
        opportunity_result = {
            "id": opportunity.id,
            "company_name": opportunity.company_name,
            "title": opportunity.title,
            "value": opportunity.value,
            "stage": opportunity.stage,
            "risk_level": opportunity.risk_level,
        }

    # ======================================================
    # CALENDAR RESULT
    # ======================================================

    calendar_result = {
        "meeting_requested": False,
        "available_slot": None,
        "existing_events": [],
    }

    for event in calendar_events:
        calendar_result["existing_events"].append(
            {
                "id": event.id,
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
                "status": event.status,
            }
        )

    # ======================================================
    # MEETING REQUEST DETECTION
    # ======================================================

    meeting_keywords = [
        "meeting",
        "demo",
        "schedule",
        "call",
        "discussion",
        "discuss",
        "meet",
        "available time",
        "available slot",
    ]

    body_lower = (
        (body or "")
        .lower()
    )

    meeting_requested = any(
        keyword in body_lower
        for keyword in meeting_keywords
    )

    calendar_result["meeting_requested"] = (
        meeting_requested
    )

    # ======================================================
    # SUGGESTED CALENDAR SLOT
    # ======================================================

    if meeting_requested:
        from datetime import datetime, timedelta

        start_time = (
            datetime.now()
            + timedelta(days=1)
        ).replace(
            hour=15,
            minute=0,
            second=0,
            microsecond=0
        )

        end_time = (
            start_time
            + timedelta(minutes=30)
        )

        calendar_result["available_slot"] = {
            "date": start_time.date().isoformat(),
            "start": start_time.strftime("%H:%M"),
            "end": end_time.strftime("%H:%M"),
        }

    # ======================================================
    # HISTORY
    # ======================================================

    history_result = {
        "email_count": history_count,
        "previous_communication_found": (
            history_count > 0
        ),
    }

    # ======================================================
    # CONTEXT GRAPH SUMMARY
    # ======================================================

    graph_result = {
        "user_email": user_email,
        "sender_email": sender_email,
        "sender_name": sender_name,
        "company_name": company_name,
        "contact_found": contact is not None,
        "crm_found": crm is not None,
        "opportunity_found": (
            opportunity is not None
        ),
        "history_email_count": history_count,
        "calendar_event_count": len(
            calendar_events
        ),
    }

    # ======================================================
    # FINAL RESULT
    # ======================================================

    return {
        "contact": contact_result,

        "company": (
            {
                "id": company.id,
                "name": company.name,
                "domain": company.domain,
                "industry": company.industry,
            }
            if company
            else (
                {
                    "id": None,
                    "name": company_name,
                    "domain": None,
                    "industry": None,
                }
                if company_name
                else None
            )
        ),

        "crm": crm_result,

        "opportunity": opportunity_result,

        "history": history_result,

        "calendar": calendar_result,

        "graph": graph_result,
    }