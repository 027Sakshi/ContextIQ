from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    DateTime,
    Float,
    ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    email_id: Mapped[int] = mapped_column(
        ForeignKey("emails.id"),
        nullable=False
    )

    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    file_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    file_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    attachment_risk: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    business_information: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )