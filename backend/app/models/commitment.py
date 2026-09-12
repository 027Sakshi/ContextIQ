from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Commitment(Base):
    __tablename__ = "commitments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"), nullable=False, index=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    direction: Mapped[str] = mapped_column(String(30), nullable=False, default="requested_from_us")
    action_text: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open", index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.6)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
