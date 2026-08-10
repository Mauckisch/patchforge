from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ServerHostKey(Base):
    __tablename__ = "server_host_keys"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    fingerprint: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
