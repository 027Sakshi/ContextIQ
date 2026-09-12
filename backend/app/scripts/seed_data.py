from datetime import datetime

from backend.app.config import settings
from backend.app.database.base import Base
from backend.app.database.connection import SessionLocal, engine
from backend.app.models.company import Company
from backend.app.models.contact import Contact
from backend.app.models.crm_record import CRMRecord
from backend.app.models.email import Email
from backend.app.models.opportunity import Opportunity
from backend.app.user_context import normalize_user_email


def seed_data(user_email: str | None = None) -> None:
    user_email = normalize_user_email(
        user_email or settings.demo_user_email
    )

    if not user_email:
        raise ValueError(
            "A demo user email is required to seed ContextIQ data."
        )

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        existing_count = (
            db.query(Email)
            .filter(Email.user_email == user_email)
            .count()
        )

        if existing_count > 0:
            print(
                f"Demo data already exists for {user_email}. Skipping seed."
            )
            return

        companies = [
            Company(user_email=user_email, name="ABC Technologies", domain="abctech.com", industry="Technology"),
            Company(user_email=user_email, name="XYZ Industries", domain="xyzindustries.com", industry="Manufacturing"),
            Company(user_email=user_email, name="Acme Solutions", domain="acmesolutions.com", industry="Software"),
        ]

        contacts = [
            Contact(user_email=user_email, name="Rahul Sharma", email="rahul@abctech.com", company="ABC Technologies"),
            Contact(user_email=user_email, name="Priya Mehta", email="priya@xyzindustries.com", company="XYZ Industries"),
            Contact(user_email=user_email, name="Arjun Patel", email="arjun@acmesolutions.com", company="Acme Solutions"),
        ]

        crm_records = [
            CRMRecord(user_email=user_email, company_name="ABC Technologies", contact_name="Rahul Sharma", deal_value=4000000, stage="Renewal", status="Active"),
            CRMRecord(user_email=user_email, company_name="XYZ Industries", contact_name="Priya Mehta", deal_value=1800000, stage="Negotiation", status="Active"),
            CRMRecord(user_email=user_email, company_name="Acme Solutions", contact_name="Arjun Patel", deal_value=750000, stage="Qualification", status="Active"),
        ]

        opportunities = [
            Opportunity(user_email=user_email, company_name="ABC Technologies", title="Annual Enterprise Renewal", value=4000000, stage="Renewal", risk_level="High"),
            Opportunity(user_email=user_email, company_name="XYZ Industries", title="Enterprise Software Deal", value=1800000, stage="Negotiation", risk_level="Medium"),
            Opportunity(user_email=user_email, company_name="Acme Solutions", title="New Software Subscription", value=750000, stage="Qualification", risk_level="Low"),
        ]

        emails = [
            Email(user_email=user_email, sender="rahul@abctech.com", recipient=user_email, subject="Annual Contract Renewal", body="Hi, our annual contract expires tomorrow. Please confirm the renewal.", received_at=datetime.now()),
            Email(user_email=user_email, sender="priya@xyzindustries.com", recipient=user_email, subject="Enterprise Software Requirement", body="We are interested in your enterprise software. We need approximately 300 licenses and would like to discuss pricing.", received_at=datetime.now()),
            Email(user_email=user_email, sender="arjun@acmesolutions.com", recipient=user_email, subject="Product Demo Request", body="We would like to schedule a product demonstration next week.", received_at=datetime.now()),
            Email(user_email=user_email, sender="unknown@example.com", recipient=user_email, subject="URGENT: Claim Your Prize", body="Congratulations! You have won a prize. Click the link immediately to claim it.", received_at=datetime.now()),
            Email(user_email=user_email, sender="support@customer-demo.com", recipient=user_email, subject="Production System Down", body="Our production system has stopped working. This is blocking our operations. Please help urgently.", received_at=datetime.now()),
        ]

        db.add_all(
            companies
            + contacts
            + crm_records
            + opportunities
            + emails
        )
        db.commit()
        print(
            f"Sample ContextIQ data inserted successfully for {user_email}."
        )

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
