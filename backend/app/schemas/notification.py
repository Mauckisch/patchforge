from typing import Literal

from pydantic import BaseModel, Field


NotificationSecurity = Literal[
    "none",
    "starttls",
    "tls",
]


class NotificationEventPreferenceResponse(BaseModel):
    event_key: str
    email_enabled: bool
    discord_enabled: bool


class NotificationEventPreferenceUpdate(BaseModel):
    event_key: str = Field(
        min_length=1,
        max_length=100,
    )

    email_enabled: bool = False
    discord_enabled: bool = False


class NotificationSettingsResponse(BaseModel):
    email_enabled: bool

    smtp_host: str | None
    smtp_port: int
    smtp_security: NotificationSecurity
    smtp_username: str | None

    smtp_password_configured: bool

    email_from: str | None
    email_recipients: list[str]

    discord_enabled: bool
    discord_webhook_configured: bool

    events: list[
        NotificationEventPreferenceResponse
    ]


class NotificationSettingsUpdate(BaseModel):
    email_enabled: bool = False

    smtp_host: str | None = Field(
        default=None,
        max_length=255,
    )

    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
    )

    smtp_security: NotificationSecurity = (
        "starttls"
    )

    smtp_username: str | None = Field(
        default=None,
        max_length=255,
    )

    # None means: keep the currently stored password.
    smtp_password: str | None = None

    email_from: str | None = Field(
        default=None,
        max_length=255,
    )

    email_recipients: list[str] = []

    discord_enabled: bool = False

    # None means: keep the currently stored webhook.
    discord_webhook_url: str | None = None

    events: list[
        NotificationEventPreferenceUpdate
    ] = []


class NotificationTestRequest(BaseModel):
    channel: Literal[
        "email",
        "discord",
    ]

    # Optional temporary Discord test value.
    discord_webhook_url: str | None = None

    # Optional temporary Email test values.
    smtp_host: str | None = None
    smtp_port: int | None = Field(
        default=None,
        ge=1,
        le=65535,
    )
    smtp_security: NotificationSecurity | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    email_from: str | None = None
    email_recipients: list[str] | None = None


class DiscordSettingsUpdate(BaseModel):
    discord_enabled: bool = False

    # None means: keep the currently stored webhook.
    discord_webhook_url: str | None = None


class EmailSettingsUpdate(BaseModel):
    email_enabled: bool = False

    smtp_host: str | None = Field(
        default=None,
        max_length=255,
    )

    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
    )

    smtp_security: NotificationSecurity = (
        "starttls"
    )

    smtp_username: str | None = Field(
        default=None,
        max_length=255,
    )

    # None means: keep the currently stored password.
    smtp_password: str | None = None

    email_from: str | None = Field(
        default=None,
        max_length=255,
    )

    email_recipients: list[str] = []


class NotificationEventsUpdate(BaseModel):
    events: list[
        NotificationEventPreferenceUpdate
    ]
