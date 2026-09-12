from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class CRMRecord(Base):
    __tablename__ = "crm_records"

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

    contact_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    deal_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    stage: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    status: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )