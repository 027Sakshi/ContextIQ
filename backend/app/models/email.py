from datetime import datetime

from sqlalchemy import String, Text, DateTime, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Email(Base):
    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint(
            "user_email",
            "gmail_message_id",
            name="uq_emails_user_gmail_message",
        ),
    )

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    # ========================================================
    # CONTEXTIQ USER
    # ========================================================

    user_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    # ========================================================
    # GMAIL MESSAGE ID
    # ========================================================

    gmail_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    # ========================================================
    # EMAIL INFORMATION
    # ========================================================

    sender: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    recipient: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    subject: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    # ========================================================
    # AI / BUSINESS INTELLIGENCE
    # ========================================================

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    spam_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    priority_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    consequence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )