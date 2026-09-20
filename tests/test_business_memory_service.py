from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.models.company import Company
from backend.app.models.contact import Contact
from backend.app.models.crm_record import CRMRecord
from backend.app.models.email import Email
from backend.app.models.opportunity import Opportunity
from backend.app.services.business_memory_service import (
    sync_business_memory_from_email,
)
from backend.app.services.context_service import (
    build_business_context,
)
from backend.app.user_context import (
    clear_current_user,
    set_current_user,
)


def make_db():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        engine
    )

    return sessionmaker(
        bind=engine
    )()


def test_new_sales_email_builds_crm_and_opportunity():
    db = make_db()

    try:
        set_current_user(
            "owner@example.com"
        )

        email = Email(
            user_email="owner@example.com",
            sender=(
                "New Buyer "
                "<newbuyer@gmail.com>"
            ),
            recipient="owner@example.com",
            subject=(
                "Pricing request "
                "for 50 licenses"
            ),
            body=(
                "We are interested in your pricing. "
                "Budget is \u20b95 lakh and "
                "we need 50 licenses."
            ),
        )

        db.add(
            email
        )

        db.commit()

        analysis = {
            "intent": "sales_inquiry",

            "entities": {
                "company": None,
                "budget": "\u20b95 lakh",
            },
        }

        threat = {
            "spam_score": 0.05,
            "phishing_score": 0.02,
        }

        result = (
            sync_business_memory_from_email(
                email=email,
                analysis=analysis,
                threat=threat,
                db=db,
            )
        )

        context = (
            build_business_context(
                email.sender,
                email.body,
                db,
            )
        )

        assert (
            result["skipped"]
            is False
        )

        assert (
            db.query(Contact)
            .filter_by(
                user_email=(
                    "owner@example.com"
                )
            )
            .count()
            == 1
        )

        assert (
            db.query(Company)
            .filter_by(
                user_email=(
                    "owner@example.com"
                )
            )
            .count()
            == 1
        )

        assert (
            db.query(CRMRecord)
            .filter_by(
                user_email=(
                    "owner@example.com"
                )
            )
            .count()
            == 1
        )

        assert (
            db.query(Opportunity)
            .filter_by(
                user_email=(
                    "owner@example.com"
                )
            )
            .count()
            == 1
        )

        assert (
            context["crm"]
            is not None
        )

        assert (
            context["opportunity"]
            is not None
        )

        assert (
            context[
                "opportunity"
            ]["value"]
            == 500000
        )

        assert (
            context[
                "company"
            ]["name"]
            == "New Buyer Account"
        )

    finally:
        clear_current_user()
        db.close()


def test_business_memory_sync_is_idempotent():
    db = make_db()

    try:
        set_current_user(
            "owner@example.com"
        )

        email = Email(
            user_email="owner@example.com",
            sender=(
                "Buyer "
                "<buyer@acme.com>"
            ),
            recipient="owner@example.com",
            subject="Need quotation",
            body=(
                "Please share pricing "
                "for 20 licenses."
            ),
        )

        db.add(
            email
        )

        db.commit()

        analysis = {
            "intent": "sales_inquiry",

            "entities": {
                "company": "Acme",
                "budget": None,
            },
        }

        threat = {
            "spam_score": 0.0,
            "phishing_score": 0.0,
        }

        sync_business_memory_from_email(
            email=email,
            analysis=analysis,
            threat=threat,
            db=db,
        )

        sync_business_memory_from_email(
            email=email,
            analysis=analysis,
            threat=threat,
            db=db,
        )

        assert (
            db.query(Contact)
            .count()
            == 1
        )

        assert (
            db.query(Company)
            .count()
            == 1
        )

        assert (
            db.query(CRMRecord)
            .count()
            == 1
        )

        assert (
            db.query(Opportunity)
            .count()
            == 1
        )

    finally:
        clear_current_user()
        db.close()


def test_security_email_does_not_create_business_records():
    db = make_db()

    try:
        set_current_user(
            "owner@example.com"
        )

        email = Email(
            user_email="owner@example.com",
            sender=(
                "Scammer "
                "<scammer@gmail.com>"
            ),
            recipient="owner@example.com",
            subject="Claim prize",
            body=(
                "Click the link immediately."
            ),
        )

        db.add(
            email
        )

        db.commit()

        result = (
            sync_business_memory_from_email(
                email=email,

                analysis={
                    "intent": (
                        "spam_or_phishing"
                    ),
                    "entities": {},
                },

                threat={
                    "spam_score": 0.95,
                    "phishing_score": 0.90,
                },

                db=db,
            )
        )

        assert result == {
            "skipped": True,
            "reason": "security_risk",
        }

        assert (
            db.query(Contact)
            .count()
            == 0
        )

        assert (
            db.query(Company)
            .count()
            == 0
        )

        assert (
            db.query(CRMRecord)
            .count()
            == 0
        )

        assert (
            db.query(Opportunity)
            .count()
            == 0
        )

    finally:
        clear_current_user()
        db.close()
