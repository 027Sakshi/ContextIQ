from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.attachment import Attachment
from backend.app.models.calendar_event import CalendarEvent
from backend.app.models.company import Company
from backend.app.models.commitment import Commitment
from backend.app.models.contact import Contact
from backend.app.models.crm_record import CRMRecord
from backend.app.models.email import Email
from backend.app.models.opportunity import Opportunity
from backend.app.services.embedding_service import hybrid_scores


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _excerpt(text: str, limit: int = 650) -> str:
    clean = " ".join(_text(text).split())
    return clean if len(clean) <= limit else clean[:limit].rstrip() + "…"


def build_business_documents(db: Session, user_email: str) -> list[dict]:
    docs: list[dict] = []

    emails = db.query(Email).filter(Email.user_email == user_email).all()
    for item in emails:
        body = _text(item.body)
        docs.append({
            "source_type": "email",
            "source_id": item.id,
            "title": item.subject or "Untitled email",
            "text": f"Email subject: {item.subject}\nFrom: {item.sender}\nCategory: {item.category or ''}\nBody: {body}",
            "metadata": {
                "sender": item.sender,
                "received_at": item.received_at.isoformat() if item.received_at else None,
                "thread_id": getattr(item, "gmail_thread_id", None),
            },
        })

    attachments = (
        db.query(Attachment, Email)
        .join(Email, Attachment.email_id == Email.id)
        .filter(Email.user_email == user_email)
        .all()
    )
    for attachment, email in attachments:
        extracted = _text(attachment.extracted_text)
        if not extracted and not attachment.summary:
            continue
        docs.append({
            "source_type": "attachment",
            "source_id": attachment.id,
            "title": attachment.filename,
            "text": (
                f"Attachment: {attachment.filename}\nRelated email: {email.subject}\n"
                f"Summary: {_text(attachment.summary)}\nContent: {extracted}\n"
                f"Business information: {_text(attachment.business_information)}"
            ),
            "metadata": {"email_id": email.id, "email_subject": email.subject},
        })

    for item in db.query(CRMRecord).filter(CRMRecord.user_email == user_email).all():
        docs.append({
            "source_type": "crm",
            "source_id": item.id,
            "title": item.company_name,
            "text": (
                f"CRM company: {item.company_name}\nContact: {item.contact_name or ''}\n"
                f"Deal value: {item.deal_value or ''}\nStage: {item.stage or ''}\nStatus: {item.status or ''}"
            ),
            "metadata": {"deal_value": item.deal_value, "stage": item.stage, "status": item.status},
        })

    for item in db.query(Opportunity).filter(Opportunity.user_email == user_email).all():
        docs.append({
            "source_type": "opportunity",
            "source_id": item.id,
            "title": item.title,
            "text": (
                f"Opportunity: {item.title}\nCompany: {item.company_name}\nValue: {item.value or ''}\n"
                f"Stage: {item.stage or ''}\nRisk level: {item.risk_level or ''}"
            ),
            "metadata": {"company": item.company_name, "value": item.value, "stage": item.stage, "risk_level": item.risk_level},
        })

    for item in db.query(CalendarEvent).filter(CalendarEvent.owner == user_email).all():
        docs.append({
            "source_type": "calendar",
            "source_id": item.id,
            "title": item.title,
            "text": (
                f"Calendar event: {item.title}\nStart: {item.event_date}\nEnd: {item.end_date}\n"
                f"Attendees: {item.attendees or ''}\nStatus: {item.status}"
            ),
            "metadata": {"start": item.event_date.isoformat(), "end": item.end_date.isoformat(), "attendees": item.attendees},
        })

    for item in db.query(Commitment).filter(Commitment.user_email == user_email).all():
        docs.append({
            "source_type": "commitment",
            "source_id": item.id,
            "title": item.action_text[:120],
            "text": (
                f"Commitment: {item.action_text}\nDirection: {item.direction}\nStatus: {item.status}\n"
                f"Due: {item.due_at or ''}\nSource: {item.source_excerpt or ''}"
            ),
            "metadata": {"status": item.status, "direction": item.direction, "due_at": item.due_at.isoformat() if item.due_at else None},
        })

    for item in db.query(Contact).filter(Contact.user_email == user_email).all():
        docs.append({
            "source_type": "contact",
            "source_id": item.id,
            "title": item.name,
            "text": f"Contact: {item.name}\nEmail: {item.email}\nCompany: {item.company or ''}",
            "metadata": {"email": item.email, "company": item.company},
        })

    for item in db.query(Company).filter(Company.user_email == user_email).all():
        docs.append({
            "source_type": "company",
            "source_id": item.id,
            "title": item.name,
            "text": f"Company: {item.name}\nDomain: {item.domain or ''}\nIndustry: {item.industry or ''}",
            "metadata": {"domain": item.domain, "industry": item.industry},
        })

    return docs


def retrieve_business_knowledge(db: Session, user_email: str, query: str, top_k: int = 8) -> dict:
    docs = build_business_documents(db, user_email)
    if not docs:
        return {"retrieval_model": "none", "evidence": [], "document_count": 0}

    scores, model_name = hybrid_scores(query, [doc["text"] for doc in docs])
    ranked = sorted(range(len(docs)), key=lambda i: float(scores[i]), reverse=True)

    evidence = []
    for index in ranked[: max(1, min(top_k, 15))]:
        score = float(scores[index])
        if score <= 0:
            continue
        item = docs[index]
        evidence.append({
            "evidence_id": f"E{len(evidence) + 1}",
            "source_type": item["source_type"],
            "source_id": item["source_id"],
            "title": item["title"],
            "score": round(score, 4),
            "excerpt": _excerpt(item["text"]),
            "metadata": item.get("metadata", {}),
        })

    return {"retrieval_model": model_name, "evidence": evidence, "document_count": len(docs)}
