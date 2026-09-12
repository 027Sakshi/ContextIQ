from datetime import datetime

from backend.app.database.connection import SessionLocal
from backend.app.models.email import Email
from backend.app.models.contact import Contact
from backend.app.models.company import Company
from backend.app.models.crm_record import CRMRecord
from backend.app.models.opportunity import Opportunity


def seed_data():
    db = SessionLocal()

    try:
        # Prevent duplicate seed data
        if db.query(Email).count() > 0:
            print("Data already exists. Skipping seed.")
            return

        # -------------------------
        # Companies
        # -------------------------
        company1 = Company(
            name="ABC Technologies",
            domain="abctech.com",
            industry="Technology"
        )

        company2 = Company(
            name="XYZ Industries",
            domain="xyzindustries.com",
            industry="Manufacturing"
        )

        company3 = Company(
            name="Acme Solutions",
            domain="acmesolutions.com",
            industry="Software"
        )

        db.add_all([company1, company2, company3])
        db.flush()

        # -------------------------
        # Contacts
        # -------------------------
        contact1 = Contact(
            name="Rahul Sharma",
            email="rahul@abctech.com",
            company="ABC Technologies"
        )

        contact2 = Contact(
            name="Priya Mehta",
            email="priya@xyzindustries.com",
            company="XYZ Industries"
        )

        contact3 = Contact(
            name="Arjun Patel",
            email="arjun@acmesolutions.com",
            company="Acme Solutions"
        )

        db.add_all([contact1, contact2, contact3])
        db.flush()

        # -------------------------
        # CRM Records
        # -------------------------
        crm1 = CRMRecord(
            company_name="ABC Technologies",
            contact_name="Rahul Sharma",
            deal_value=4000000,
            stage="Renewal",
            status="Active"
        )

        crm2 = CRMRecord(
            company_name="XYZ Industries",
            contact_name="Priya Mehta",
            deal_value=1800000,
            stage="Negotiation",
            status="Active"
        )

        crm3 = CRMRecord(
            company_name="Acme Solutions",
            contact_name="Arjun Patel",
            deal_value=750000,
            stage="Qualification",
            status="Active"
        )

        db.add_all([crm1, crm2, crm3])
        db.flush()

        # -------------------------
        # Opportunities
        # -------------------------
        opportunity1 = Opportunity(
            company_name="ABC Technologies",
            title="Annual Enterprise Renewal",
            value=4000000,
            stage="Renewal",
            risk_level="High"
        )

        opportunity2 = Opportunity(
            company_name="XYZ Industries",
            title="Enterprise Software Deal",
            value=1800000,
            stage="Negotiation",
            risk_level="Medium"
        )

        opportunity3 = Opportunity(
            company_name="Acme Solutions",
            title="New Software Subscription",
            value=750000,
            stage="Qualification",
            risk_level="Low"
        )

        db.add_all([
            opportunity1,
            opportunity2,
            opportunity3
        ])
        db.flush()

        # -------------------------
        # Emails
        # -------------------------
        emails = [
            Email(
                sender="rahul@abctech.com",
                recipient="sales@contextiq-demo.com",
                subject="Annual Contract Renewal",
                body=(
                    "Hi, our annual contract expires tomorrow. "
                    "Please confirm the renewal."
                ),
                received_at=datetime.now()
            ),

            Email(
                sender="priya@xyzindustries.com",
                recipient="sales@contextiq-demo.com",
                subject="Enterprise Software Requirement",
                body=(
                    "We are interested in your enterprise software. "
                    "We need approximately 300 licenses and would like "
                    "to discuss pricing."
                ),
                received_at=datetime.now()
            ),

            Email(
                sender="arjun@acmesolutions.com",
                recipient="sales@contextiq-demo.com",
                subject="Product Demo Request",
                body=(
                    "We would like to schedule a product demonstration "
                    "next week."
                ),
                received_at=datetime.now()
            ),

            Email(
                sender="unknown@example.com",
                recipient="sales@contextiq-demo.com",
                subject="URGENT: Claim Your Prize",
                body=(
                    "Congratulations! You have won a prize. "
                    "Click the link immediately to claim it."
                ),
                received_at=datetime.now()
            ),

            Email(
                sender="support@customer-demo.com",
                recipient="support@contextiq-demo.com",
                subject="Production System Down",
                body=(
                    "Our production system has stopped working. "
                    "This is blocking our operations. Please help urgently."
                ),
                received_at=datetime.now()
            )
        ]

        db.add_all(emails)

        db.commit()

        print("Sample ContextIQ data inserted successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error inserting data: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_data()