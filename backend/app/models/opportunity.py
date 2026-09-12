from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    user_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    stage: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    risk_level: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )