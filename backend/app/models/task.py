from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    server_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    schedule_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    timezone: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="UTC",
    )

    run_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    hour: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    minute: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    weekday: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    day_of_month: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    notify_only_on_updates: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
