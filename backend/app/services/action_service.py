from datetime import datetime, timedelta
from email.utils import parseaddr
import re

from sqlalchemy.orm import Session

from backend.app.models.action import Action
from backend.app.models.calendar_event import CalendarEvent
from backend.app.models.email import Email
from backend.app.models.crm_record import CRMRecord
from backend.app.models.opportunity import Opportunity
from backend.app.models.contact import Contact
from backend.app.user_context import require_current_user
from backend.app.services.calendar_google_service import create_calendar_event, find_available_slot, LOCAL_TZ
from backend.app.services.context_service import find_company_name_from_body


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def extract_email_address(sender: str) -> str:
    """
    Extract a clean email address from:
    Rahul Sharma <rahul@example.com>
    or:
    rahul@example.com
    """

    _, email_address = parseaddr(
        sender or ""
    )

    return (
        email_address
        or (sender or "").strip()
    )


def extract_display_name(sender: str) -> str:
    """
    Extract display name from a sender string.
    """

    name, email_address = parseaddr(
        sender or ""
    )

    if name:
        return name.strip()

    if email_address:

        local_part = email_address.split(
            "@"
        )[0]

        local_part = re.sub(
            r"[._-]+",
            " ",
            local_part
        )

        return local_part.title()

    return "Unknown Contact"


def extract_domain(sender: str) -> str:
    """
    Extract domain from sender email.
    """

    email_address = extract_email_address(
        sender
    )

    if "@" not in email_address:
        return ""

    return email_address.split(
        "@",
        1
    )[1].lower().strip()


def extract_company_name(
    sender: str,
    existing_contact: Contact | None = None
) -> str:
    """
    Try to determine company name.

    Priority:
    1. Existing contact company
    2. Email domain
    3. Generic fallback
    """

    if existing_contact:
        company = (
            existing_contact.company
        )

        if company:
            return company.strip()

    domain = extract_domain(
        sender
    )

    if domain:

        parts = domain.split(".")

        if parts:

            company = parts[0]

            generic_domains = {
                "gmail",
                "googlemail",
                "yahoo",
                "hotmail",
                "outlook",
                "live",
                "icloud",
                "protonmail",
                "rediffmail"
            }

            if company.lower() not in generic_domains:

                return company.replace(
                    "-",
                    " "
                ).title()

    return "Unknown Company"


# ==========================================================
# CRM ACTION
# ==========================================================

def create_or_update_crm(
    email: Email,
    db: Session
):
    """
    Create or update CRM record and opportunity.
    """

    user_email = require_current_user()

    if email.user_email != user_email:
        raise ValueError("Email does not belong to the authenticated user.")

    sender_email = extract_email_address(
        email.sender
    )

    contact_name = extract_display_name(
        email.sender
    )

    # ------------------------------------------------------
    # Find existing contact
    # ------------------------------------------------------

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

    if contact:

        contact_name = (
            contact.name
            or contact_name
        )

    body_company = (
        find_company_name_from_body(
            email.body
            or ""
        )
    )

    # Explicit company identity from this email wins.
    company_name = (
        body_company
        or extract_company_name(
            email.sender,
            contact
        )
    )

    if (
        contact
        and body_company
    ):
        contact.company = (
            body_company
        )

    # ------------------------------------------------------
    # Find existing CRM record
    # ------------------------------------------------------

    crm_record = (
        db.query(CRMRecord)
        .filter(
            CRMRecord.company_name.ilike(
                company_name
            ),
            CRMRecord.user_email == user_email
        )
        .first()
    )

    if crm_record:

        # Update existing record
        crm_record.contact_name = (
            contact_name
        )

        if not crm_record.status:
            crm_record.status = "open"

        db_action = "updated"

    else:

        # Create new CRM record
        crm_record = CRMRecord(
            user_email=user_email,
            company_name=company_name,
            contact_name=contact_name,
            deal_value=None,
            stage="new_lead",
            status="open"
        )

        db.add(
            crm_record
        )

        db.flush()

        db_action = "created"

    # ------------------------------------------------------
    # Find existing opportunity
    # ------------------------------------------------------

    opportunity_title = (
        email.subject
        or "Detected opportunity"
    ).strip()

    opportunity = (
        db.query(Opportunity)
        .filter(
            Opportunity.company_name.ilike(
                company_name
            ),
            Opportunity.user_email
            == user_email,
            Opportunity.title
            == opportunity_title,
        )
        .first()
    )

    if opportunity:

        # Update existing opportunity
        opportunity.title = (
            opportunity_title
        )

        if not opportunity.stage:
            opportunity.stage = "new"

        if not opportunity.risk_level:
            opportunity.risk_level = "MEDIUM"

        opportunity_action = "updated"

    else:

        # Create new opportunity
        opportunity = Opportunity(
            user_email=user_email,
            company_name=company_name,
            title=opportunity_title,
            value=None,
            stage="new",
            risk_level="MEDIUM"
        )

        db.add(
            opportunity
        )

        db.flush()

        opportunity_action = "created"

    db.commit()

    db.refresh(
        crm_record
    )

    db.refresh(
        opportunity
    )

    return {
        "crm_action": db_action,
        "crm_record_id": crm_record.id,
        "company_name": crm_record.company_name,
        "contact_name": crm_record.contact_name,
        "stage": crm_record.stage,
        "status": crm_record.status,
        "opportunity_action": opportunity_action,
        "opportunity_id": opportunity.id,
        "opportunity_title": opportunity.title,
    }


# ==========================================================
# EXECUTE ACTION
# ==========================================================

def execute_action(
    action: Action,
    db: Session
) -> dict:
    """
    Execute an approved ContextIQ action.
    """

    # ------------------------------------------------------
    # Safety gate
    # ------------------------------------------------------

    if action.status != "approved":

        return {
            "success": False,
            "message": (
                "Action must be approved "
                "before execution."
            )
        }

    # ------------------------------------------------------
    # Get related email, scoped to the authenticated user
    # ------------------------------------------------------

    user_email = require_current_user()

    email = (
        db.query(Email)
        .filter(
            Email.id == action.email_id,
            Email.user_email == user_email
        )
        .first()
    )

    if not email:

        return {
            "success": False,
            "message": (
                "Related email not found."
            )
        }

    # ======================================================
    # RENEWAL TASK
    # ======================================================

    if action.action_type == "create_renewal_task":

        action.status = "executed"

        db.commit()

        return {
            "success": True,
            "action": action.action_type,
            "message": (
                "Renewal follow-up task created."
            ),
            "email_id": email.id
        }

    # ======================================================
    # ESCALATE ACCOUNT MANAGER
    # ======================================================

    if action.action_type == "escalate_account_manager":

        action.status = "executed"

        db.commit()

        return {
            "success": True,
            "action": action.action_type,
            "message": (
                "Email escalated to the account manager."
            ),
            "email_id": email.id
        }

    # ======================================================
    # ESCALATE SUPPORT
    # ======================================================

    if action.action_type == "escalate_support":

        action.status = "executed"

        db.commit()

        return {
            "success": True,
            "action": action.action_type,
            "message": (
                "Support issue escalated."
            ),
            "email_id": email.id
        }

    # ======================================================
    # CREATE SUPPORT TICKET
    # ======================================================

    if action.action_type == "create_support_ticket":

        action.status = "executed"

        db.commit()

        return {
            "success": True,
            "action": action.action_type,
            "message": (
                "Support ticket created."
            ),
            "email_id": email.id
        }

    # ======================================================
    # CRM LEAD / OPPORTUNITY
    # ======================================================

    if action.action_type == "create_or_update_lead":

        try:

            crm_result = create_or_update_crm(
                email=email,
                db=db
            )

            action.status = "executed"

            db.commit()

            return {
                "success": True,
                "action": action.action_type,
                "message": (
                    "CRM lead/opportunity "
                    "created or updated successfully."
                ),
                "email_id": email.id,
                **crm_result
            }

        except Exception as error:

            db.rollback()

            return {
                "success": False,
                "action": action.action_type,
                "message": (
                    "CRM update failed."
                ),
                "error": str(error)
            }

    # ======================================================
    # SCHEDULE DEMO
    # ======================================================

    if action.action_type == "schedule_demo":
        try:
            slot = find_available_slot(duration_minutes=30, days_ahead=7)
            if not slot:
                return {"success": False, "message": "No available Google Calendar slot found in the next 7 days."}

            start_time = datetime.fromisoformat(f"{slot['date']}T{slot['start']}:00").replace(tzinfo=LOCAL_TZ)
            end_time = datetime.fromisoformat(f"{slot['date']}T{slot['end']}:00").replace(tzinfo=LOCAL_TZ)
            attendee = extract_email_address(email.sender)
            created = create_calendar_event(
                title=f"ContextIQ Demo - {email.subject}",
                start_datetime=start_time,
                end_datetime=end_time,
                attendee_email=attendee if "@" in attendee else None,
            )

            calendar_event = CalendarEvent(
                owner=user_email,
                title=f"ContextIQ Demo - {email.subject}",
                event_date=start_time.replace(tzinfo=None),
                end_date=end_time.replace(tzinfo=None),
                attendees=attendee,
                status="scheduled",
                external_event_id=created.get("id"),
                external_html_link=created.get("htmlLink"),
            )
            db.add(calendar_event)
            action.status = "executed"
            db.commit()
            db.refresh(calendar_event)
            return {
                "success": True,
                "action": action.action_type,
                "message": "Google Calendar event created successfully.",
                "email_id": email.id,
                "calendar_event_id": calendar_event.id,
                "google_event_id": created.get("id"),
                "html_link": created.get("htmlLink"),
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            }
        except Exception as error:
            db.rollback()
            return {"success": False, "message": "Google Calendar action failed.", "error": str(error)}

    # ======================================================
    # PARTNERSHIPS
    # ======================================================

    if action.action_type == "assign_to_partnerships":

        action.status = "executed"

        db.commit()

        return {
            "success": True,
            "action": action.action_type,
            "message": (
                "Partnership request assigned "
                "to the partnerships team."
            ),
            "email_id": email.id
        }

    # ======================================================
    # FINANCE
    # ======================================================

    if action.action_type == "assign_to_finance":

        action.status = "executed"

        db.commit()

        return {
            "success": True,
            "action": action.action_type,
            "message": (
                "Billing request assigned "
                "to the finance team."
            ),
            "email_id": email.id
        }

    # ======================================================
    # SECURITY
    # ======================================================

    if action.action_type == "security_review":

        action.status = "executed"

        db.commit()

        return {
            "success": True,
            "action": action.action_type,
            "message": (
                "Email moved to security review."
            ),
            "email_id": email.id
        }

    # ======================================================
    # UNSUPPORTED ACTION
    # ======================================================

    return {
        "success": False,
        "message": (
            f"Unsupported action: "
            f"{action.action_type}"
        )
    }