from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    user_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    company: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )