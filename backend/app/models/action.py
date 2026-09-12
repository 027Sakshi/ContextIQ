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


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    email_id: Mapped[int] = mapped_column(
        ForeignKey("emails.id"),
        nullable=False
    )

    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    risk_level: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="pending"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )