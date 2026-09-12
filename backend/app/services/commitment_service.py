from __future__ import annotations

import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.models.commitment import Commitment
from backend.app.models.email import Email

_REQUEST_PATTERNS = [
    r"\bplease\s+(?:can\s+you\s+|could\s+you\s+|send\s+|share\s+|confirm\s+|provide\s+|review\s+|update\s+)([^.!?\n]{5,180})",
    r"\b(?:can|could|would)\s+you\s+([^.!?\n]{5,180})",
    r"\bwe\s+need\s+(?:you\s+to\s+)?([^.!?\n]{5,180})",
]
_EXTERNAL_PATTERNS = [
    r"\b(?:i|we)\s+(?:will|'ll)\s+([^.!?\n]{5,180})",
    r"\b(?:i|we)\s+can\s+([^.!?\n]{5,180})",
]


def _due_at(text: str, base: datetime | None) -> datetime | None:
    base = base or datetime.now()
    lowered = text.lower()
    if "tomorrow" in lowered:
        return (base + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
    match = re.search(r"\bby\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", lowered)
    if match:
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        target = days.index(match.group(1))
        delta = (target - base.weekday()) % 7 or 7
        return (base + timedelta(days=delta)).replace(hour=17, minute=0, second=0, microsecond=0)
    return None


def extract_commitments(email: Email) -> list[dict]:
    text = f"{email.subject}\n{email.body or ''}"
    items: list[dict] = []
    seen: set[str] = set()

    for direction, patterns in [
        ("requested_from_us", _REQUEST_PATTERNS),
        ("external_commitment", _EXTERNAL_PATTERNS),
    ]:
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.I):
                action = " ".join(match.group(1).strip(" :-").split())
                key = action.lower()
                if len(action) < 5 or key in seen:
                    continue
                seen.add(key)
                excerpt_start = max(0, match.start() - 80)
                excerpt_end = min(len(text), match.end() + 100)
                items.append({
                    "direction": direction,
                    "action_text": action[:500],
                    "due_at": _due_at(text[match.start():match.end() + 120], email.received_at),
                    "confidence": 0.72 if direction == "requested_from_us" else 0.67,
                    "source_excerpt": " ".join(text[excerpt_start:excerpt_end].split())[:700],
                })
    return items[:6]


def sync_email_commitments(db: Session, email: Email) -> list[Commitment]:
    db.query(Commitment).filter(
        Commitment.user_email == email.user_email,
        Commitment.email_id == email.id,
        Commitment.status == "open",
    ).delete(synchronize_session=False)

    records = []
    for item in extract_commitments(email):
        record = Commitment(
            user_email=email.user_email,
            email_id=email.id,
            thread_id=getattr(email, "gmail_thread_id", None),
            **item,
        )
        db.add(record)
        records.append(record)
    return records
