from datetime import datetime

from backend.app.models.email import Email
from backend.app.services.commitment_service import extract_commitments


def test_extracts_requested_commitment():
    email = Email(
        user_email="u@example.com",
        sender="client@example.com",
        recipient="u@example.com",
        subject="Renewal",
        body="Could you send the revised contract by tomorrow?",
        received_at=datetime(2026, 9, 13, 10, 0),
    )
    items = extract_commitments(email)
    assert items
    assert items[0]["direction"] == "requested_from_us"
