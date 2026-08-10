from sqlalchemy import (
    Boolean,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
    )

    email_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    smtp_host: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    smtp_port: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=587,
    )

    smtp_security: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="starttls",
    )

    smtp_username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    smtp_password_nonce: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )

    smtp_password_ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )

    email_from: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    email_recipients: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    discord_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    discord_webhook_nonce: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )

    discord_webhook_ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
    )


class NotificationEventPreference(Base):
    __tablename__ = "notification_event_preferences"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    event_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    email_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    discord_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
