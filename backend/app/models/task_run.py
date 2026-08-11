from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # Intentionally not a foreign key:
    # task run history should survive task deletion.
    task_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    # Snapshot values preserve meaningful history even if
    # the scheduled task is renamed or deleted later.
    task_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="RUNNING",
    )

    target_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    success_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    failed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    updates_found: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )


class TaskRunResult(Base):
    __tablename__ = "task_run_results"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    run_id: Mapped[int] = mapped_column(
        ForeignKey(
            "task_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # Snapshot the server identity so run history remains
    # understandable after a managed server is removed.
    server_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    server_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    host: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    update_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # JSON-encoded list of package/update names.
    # Used by CHECK task details.
    updates_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    installed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # JSON-encoded list of packages actually installed
    # during INSTALL_ALL.
    installed_packages_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    remaining_updates: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    cleanup_available: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    reboot_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
