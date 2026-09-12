from __future__ import annotations

import base64
from email.message import EmailMessage
from email.utils import parseaddr

from backend.app.services.gmail_service import get_gmail_service


def create_gmail_draft(recipient: str, subject: str, body: str) -> dict:
    _, clean_recipient = parseaddr(recipient or "")
    clean_recipient = clean_recipient or (recipient or "").strip()
    if not clean_recipient or "@" not in clean_recipient:
        raise ValueError("A valid recipient email address is required.")

    message = EmailMessage()
    message["To"] = clean_recipient
    message["Subject"] = subject.strip() or "Re:"
    message.set_content(body.strip())

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    created = (
        get_gmail_service()
        .users()
        .drafts()
        .create(userId="me", body={"message": {"raw": raw}})
        .execute()
    )
    return {
        "draft_id": created.get("id"),
        "message_id": (created.get("message") or {}).get("id"),
        "recipient": clean_recipient,
        "subject": message["Subject"],
    }
