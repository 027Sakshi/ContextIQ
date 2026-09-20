from __future__ import annotations

import re
from email.utils import parseaddr

from sqlalchemy.orm import Session

from backend.app.models.company import Company
from backend.app.models.contact import Contact
from backend.app.models.crm_record import CRMRecord
from backend.app.models.email import Email
from backend.app.models.opportunity import Opportunity
from backend.app.user_context import require_current_user


GENERIC_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "icloud.com",
    "protonmail.com",
    "rediffmail.com",
}

ACCOUNT_INTENTS = {
    "customer_renewal",
    "sales_inquiry",
    "product_demo",
    "partnership",
    "support_request",
}

OPPORTUNITY_INTENTS = {
    "customer_renewal",
    "sales_inquiry",
    "product_demo",
    "partnership",
}

STAGE_BY_INTENT = {
    "customer_renewal": "Renewal",
    "sales_inquiry": "Qualification",
    "product_demo": "Discovery",
    "partnership": "Partnership",
    "support_request": "Customer Success",
}

RISK_BY_INTENT = {
    "customer_renewal": "HIGH",
    "sales_inquiry": "MEDIUM",
    "product_demo": "MEDIUM",
    "partnership": "MEDIUM",
}

COMPANY_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9&.'-]*"
    r"(?:\s+[A-Z][A-Za-z0-9&.'-]*){0,4})\s+"
    r"(Technologies|Industries|Corporation|Corp|Solutions|Systems|"
    r"Ltd|Limited|Inc|Labs|Software|Enterprises|Group|Networks|"
    r"Consulting)\b"
)


def _sender_parts(
    sender: str,
) -> tuple[str, str, str]:
    name, address = parseaddr(
        sender or ""
    )

    address = (
        address
        or sender
        or ""
    ).strip().lower()

    if "@" not in address:
        return (
            name.strip()
            or "Unknown Contact",
            address,
            "",
        )

    if not name.strip():
        local = address.split(
            "@",
            1,
        )[0]

        name = re.sub(
            r"[._+-]+",
            " ",
            local,
        ).strip().title()

    domain = address.split(
        "@",
        1,
    )[1].strip().lower()

    return (
        name.strip()
        or "Unknown Contact",
        address,
        domain,
    )


def _company_from_body(
    body: str,
) -> str | None:
    if not body:
        return None

    match = COMPANY_PATTERN.search(
        body
    )

    if not match:
        return None

    return match.group(
        0
    ).strip()


def _company_from_domain(
    domain: str,
) -> str | None:
    if (
        not domain
        or domain
        in GENERIC_EMAIL_DOMAINS
    ):
        return None

    label = domain.split(
        ".",
        1,
    )[0]

    label = re.sub(
        r"[-_]+",
        " ",
        label,
    ).strip()

    return (
        label.title()
        if label
        else None
    )


def _parse_budget(
    value: object,
) -> float | None:
    if value is None:
        return None

    text = (
        str(value)
        .strip()
        .lower()
        .replace(",", "")
    )

    if not text:
        return None

    match = re.search(
        r"(?:\u20b9|rs\.?|inr)?\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*"
        r"(crore|cr|lakh|lac|l)?\b",
        text,
    )

    if not match:
        return None

    amount = float(
        match.group(1)
    )

    unit = (
        match.group(2)
        or ""
    ).lower()

    if unit in {
        "crore",
        "cr",
    }:
        amount *= 10_000_000

    elif unit in {
        "lakh",
        "lac",
        "l",
    }:
        amount *= 100_000

    return amount


def sync_business_memory_from_email(
    *,
    email: Email,
    analysis: dict,
    threat: dict,
    db: Session,
) -> dict:
    """
    Maintain ContextIQ's INTERNAL user-scoped business memory.

    This is not an external side effect.

    Gmail drafts, Calendar events and other external actions
    remain protected by ContextIQ's human approval workflow.
    """

    user_email = require_current_user()

    if email.user_email != user_email:
        raise ValueError(
            "Email does not belong to "
            "the authenticated user."
        )

    spam_score = float(
        threat.get(
            "spam_score"
        )
        or 0
    )

    phishing_score = float(
        threat.get(
            "phishing_score"
        )
        or 0
    )

    # Never turn security-risk mail into business memory.
    if max(
        spam_score,
        phishing_score,
    ) >= 0.80:
        return {
            "skipped": True,
            "reason": "security_risk",
        }

    intent = str(
        analysis.get(
            "intent"
        )
        or "general_inquiry"
    )

    entities = (
        analysis.get(
            "entities"
        )
        or {}
    )

    (
        sender_name,
        sender_email,
        sender_domain,
    ) = _sender_parts(
        email.sender
    )

    if (
        not sender_email
        or "@"
        not in sender_email
    ):
        return {
            "skipped": True,
            "reason": "no_sender_email",
        }

    # -----------------------------------------------------
    # CONTACT
    # -----------------------------------------------------

    contact = (
        db.query(
            Contact
        )
        .filter(
            Contact.user_email
            == user_email,
            Contact.email.ilike(
                sender_email
            ),
        )
        .first()
    )

    body_company = (
        _company_from_body(
            email.body
            or ""
        )
    )

    entity_company = str(
        entities.get(
            "company"
        )
        or ""
    ).strip() or None

    domain_company = (
        _company_from_domain(
            sender_domain
        )
    )

    company_name = (
        (
            contact.company.strip()
            if (
                contact
                and contact.company
            )
            else None
        )
        or body_company
        or entity_company
        or domain_company
    )

    # Personal Gmail/Outlook addresses are very common for
    # founders, SMB buyers and hackathon demo users.
    #
    # For a genuine business signal, create a stable account
    # identity rather than putting everybody into one
    # "Unknown Company" bucket.
    if (
        not company_name
        and intent
        in ACCOUNT_INTENTS
    ):
        company_name = (
            f"{sender_name} Account"
        )

    if contact is None:
        contact = Contact(
            user_email=user_email,
            name=sender_name,
            email=sender_email,
            company=company_name,
        )

        db.add(
            contact
        )

        db.flush()

    else:
        if (
            sender_name
            and sender_name
            != "Unknown Contact"
        ):
            contact.name = (
                sender_name
            )

        if company_name:
            contact.company = (
                company_name
            )

    # -----------------------------------------------------
    # COMPANY
    # -----------------------------------------------------

    company = None

    if company_name:
        company = (
            db.query(
                Company
            )
            .filter(
                Company.user_email
                == user_email,
                Company.name.ilike(
                    company_name
                ),
            )
            .first()
        )

        if company is None:
            company = Company(
                user_email=user_email,
                name=company_name,
                domain=(
                    None
                    if sender_domain
                    in GENERIC_EMAIL_DOMAINS
                    else (
                        sender_domain
                        or None
                    )
                ),
                industry=None,
            )

            db.add(
                company
            )

            db.flush()

        elif (
            not company.domain
            and sender_domain
            and sender_domain
            not in GENERIC_EMAIL_DOMAINS
        ):
            company.domain = (
                sender_domain
            )

    # -----------------------------------------------------
    # CRM ACCOUNT
    # -----------------------------------------------------

    crm_record = None

    opportunity = None

    budget_value = (
        _parse_budget(
            entities.get(
                "budget"
            )
        )
    )

    if (
        company_name
        and intent
        in ACCOUNT_INTENTS
    ):
        crm_record = (
            db.query(
                CRMRecord
            )
            .filter(
                CRMRecord.user_email
                == user_email,
                CRMRecord.company_name.ilike(
                    company_name
                ),
            )
            .first()
        )

        stage = (
            STAGE_BY_INTENT[
                intent
            ]
        )

        if crm_record is None:
            crm_record = CRMRecord(
                user_email=user_email,
                company_name=company_name,
                contact_name=sender_name,
                deal_value=budget_value,
                stage=stage,
                status="Active",
            )

            db.add(
                crm_record
            )

            db.flush()

        else:
            # Preserve established CRM state. Re-analysis of older
            # messages must not overwrite newer/manual account state.
            if not crm_record.contact_name:
                crm_record.contact_name = (
                    sender_name
                )

            if not crm_record.stage:
                crm_record.stage = (
                    stage
                )

            if not crm_record.status:
                crm_record.status = (
                    "Active"
                )

            if (
                crm_record.deal_value
                is None
                and budget_value
                is not None
            ):
                crm_record.deal_value = (
                    budget_value
                )

    # -----------------------------------------------------
    # OPPORTUNITY
    # -----------------------------------------------------

    if (
        company_name
        and intent
        in OPPORTUNITY_INTENTS
    ):
        opportunity = (
            db.query(
                Opportunity
            )
            .filter(
                Opportunity.user_email
                == user_email,
                Opportunity.company_name.ilike(
                    company_name
                ),
            )
            .first()
        )

        stage = (
            STAGE_BY_INTENT[
                intent
            ]
        )

        risk = (
            RISK_BY_INTENT[
                intent
            ]
        )

        if opportunity is None:
            opportunity = Opportunity(
                user_email=user_email,
                company_name=company_name,
                title=(
                    email.subject
                    or "Detected opportunity"
                ),
                value=budget_value,
                stage=stage,
                risk_level=risk,
            )

            db.add(
                opportunity
            )

            db.flush()

        else:
            # Keep established opportunity state stable when
            # historical emails are re-analyzed.
            if not opportunity.title:
                opportunity.title = (
                    email.subject
                    or "Detected opportunity"
                )

            if not opportunity.stage:
                opportunity.stage = (
                    stage
                )

            if not opportunity.risk_level:
                opportunity.risk_level = (
                    risk
                )

            if (
                opportunity.value
                is None
                and budget_value
                is not None
            ):
                opportunity.value = (
                    budget_value
                )

    db.flush()

    return {
        "skipped": False,

        "contact_id": (
            contact.id
            if contact
            else None
        ),

        "company_id": (
            company.id
            if company
            else None
        ),

        "crm_record_id": (
            crm_record.id
            if crm_record
            else None
        ),

        "opportunity_id": (
            opportunity.id
            if opportunity
            else None
        ),

        "company_name": (
            company_name
        ),
    }
