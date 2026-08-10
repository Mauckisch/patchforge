from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.core.database import Base


class ServerUpdate(Base):
    __tablename__ = "server_updates"

    __table_args__ = (
        UniqueConstraint(
            "server_id",
            "name",
            name="uq_server_update_package",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    server_id: Mapped[int] = mapped_column(
        ForeignKey(
            "servers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    installed_version: Mapped[str] = (
        mapped_column(
            String(255),
            nullable=False,
        )
    )

    available_version: Mapped[str] = (
        mapped_column(
            String(255),
            nullable=False,
        )
    )

    held: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    checked_at: Mapped[datetime] = (
        mapped_column(
            DateTime,
            nullable=False,
            default=datetime.utcnow,
        )
    )
