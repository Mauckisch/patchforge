from sqlalchemy import ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ServerCredential(Base):
    __tablename__ = "server_credentials"

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

    ssh_password_nonce: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )

    ssh_password_ciphertext: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )

    privilege_method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="auto",
    )

    privilege_password_nonce: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )

    privilege_password_ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )
