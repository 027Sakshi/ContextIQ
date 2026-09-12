from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.models.contact import Contact
from backend.app.models.email import Email
from backend.app.services.action_service import create_or_update_crm
from backend.app.user_context import clear_current_user, set_current_user


def make_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_crm_action_does_not_reuse_another_users_contact():
    db = make_db()

    try:
        db.add(
            Contact(
                user_email="other@example.com",
                name="Other User Contact",
                email="buyer@acme.com",
                company="Wrong Company",
            )
        )
        email = Email(
            user_email="me@example.com",
            sender="Buyer <buyer@acme.com>",
            recipient="me@example.com",
            subject="Pricing request",
            body="Please send pricing.",
        )
        db.add(email)
        db.commit()

        set_current_user("me@example.com")
        result = create_or_update_crm(email, db)

        assert result["company_name"] != "Wrong Company"
        assert result["company_name"] == "Acme"

    finally:
        clear_current_user()
        db.close()
