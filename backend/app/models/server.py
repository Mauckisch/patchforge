from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    host: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    ssh_port: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=22,
    )

    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    system_hostname: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    distribution: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    distribution_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    package_manager: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    architecture: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    kernel_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    reboot_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    cleanup_available: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        default=None,
    )

    connection_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="UNKNOWN",
    )

    updates_available: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    updates_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    last_check_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
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
