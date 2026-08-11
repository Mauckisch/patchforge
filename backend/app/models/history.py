from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HistoryEntry(Base):
    __tablename__ = "history"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    server_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    server_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    task_run_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    package_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    reboot_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
