from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScheduledTaskTarget(Base):
    __tablename__ = "scheduled_task_targets"

    __table_args__ = (
        UniqueConstraint(
            "task_id",
            "server_id",
            name="uq_scheduled_task_target",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey(
            "scheduled_tasks.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    server_id: Mapped[int] = mapped_column(
        ForeignKey(
            "servers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
