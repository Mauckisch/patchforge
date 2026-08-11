from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.credentials import encrypt_secret
from app.models.notification import (
    NotificationEventPreference,
    NotificationSettings,
)
from app.schemas.notification import (
    NotificationSettingsUpdate,
)


EVENT_SERVER_OFFLINE = "SERVER_OFFLINE"
EVENT_SERVER_ONLINE = "SERVER_ONLINE"
EVENT_SSH_ERROR = "SSH_ERROR"
EVENT_UPDATES_AVAILABLE = "UPDATES_AVAILABLE"
EVENT_INSTALL_SUCCESS = "INSTALL_SUCCESS"
EVENT_INSTALL_FAILED = "INSTALL_FAILED"
EVENT_CLEANUP_AVAILABLE = "CLEANUP_AVAILABLE"
EVENT_CLEANUP_SUCCESS = "CLEANUP_SUCCESS"
EVENT_CLEANUP_FAILED = "CLEANUP_FAILED"
EVENT_REBOOT_REQUIRED = "REBOOT_REQUIRED"
EVENT_TASK_SUCCESS = "TASK_SUCCESS"
EVENT_TASK_FAILED = "TASK_FAILED"


NOTIFICATION_EVENTS = (
    EVENT_SERVER_OFFLINE,
    EVENT_SERVER_ONLINE,
    EVENT_SSH_ERROR,
    EVENT_UPDATES_AVAILABLE,
    EVENT_INSTALL_SUCCESS,
    EVENT_INSTALL_FAILED,
    EVENT_CLEANUP_AVAILABLE,
    EVENT_CLEANUP_SUCCESS,
    EVENT_CLEANUP_FAILED,
    EVENT_REBOOT_REQUIRED,
    EVENT_TASK_SUCCESS,
    EVENT_TASK_FAILED,
)


def get_notification_settings(
    db: Session,
) -> NotificationSettings:
    settings = db.get(
        NotificationSettings,
        1,
    )

    if settings is None:
        settings = NotificationSettings(
            id=1,
        )

        db.add(settings)
        db.commit()
        db.refresh(settings)

    ensure_event_preferences(
        db
    )

    return settings


def ensure_event_preferences(
    db: Session,
) -> None:
    existing = set(
        db.scalars(
            select(
                NotificationEventPreference.event_key
            )
        ).all()
    )

    changed = False

    for event_key in NOTIFICATION_EVENTS:
        if event_key in existing:
            continue

        db.add(
            NotificationEventPreference(
                event_key=event_key,
                email_enabled=False,
                discord_enabled=False,
            )
        )

        changed = True

    if changed:
        db.commit()


def get_event_preferences(
    db: Session,
) -> list[NotificationEventPreference]:
    ensure_event_preferences(
        db
    )

    preferences = list(
        db.scalars(
            select(
                NotificationEventPreference
            ).order_by(
                NotificationEventPreference.id
            )
        ).all()
    )

    return preferences


def _normalize_optional_string(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = value.strip()

    return value or None


def _normalize_recipients(
    recipients: list[str],
) -> list[str]:
    result: list[str] = []

    for recipient in recipients:
        recipient = recipient.strip()

        if (
            recipient
            and recipient not in result
        ):
            result.append(
                recipient
            )

    return result


def update_notification_settings(
    db: Session,
    payload: NotificationSettingsUpdate,
) -> NotificationSettings:
    settings = get_notification_settings(
        db
    )

    settings.email_enabled = (
        payload.email_enabled
    )

    settings.smtp_host = (
        _normalize_optional_string(
            payload.smtp_host
        )
    )

    settings.smtp_port = (
        payload.smtp_port
    )

    settings.smtp_security = (
        payload.smtp_security
    )

    settings.smtp_username = (
        _normalize_optional_string(
            payload.smtp_username
        )
    )

    settings.email_from = (
        _normalize_optional_string(
            payload.email_from
        )
    )

    recipients = _normalize_recipients(
        payload.email_recipients
    )

    settings.email_recipients = (
        "\n".join(recipients)
        if recipients
        else None
    )

    settings.discord_enabled = (
        payload.discord_enabled
    )

    if payload.smtp_password is not None:
        password = payload.smtp_password.strip()

        if password:
            nonce, ciphertext = (
                encrypt_secret(
                    password
                )
            )

            settings.smtp_password_nonce = (
                nonce
            )

            settings.smtp_password_ciphertext = (
                ciphertext
            )

    if payload.discord_webhook_url is not None:
        webhook = (
            payload.discord_webhook_url.strip()
        )

        if webhook:
            nonce, ciphertext = (
                encrypt_secret(
                    webhook
                )
            )

            settings.discord_webhook_nonce = (
                nonce
            )

            settings.discord_webhook_ciphertext = (
                ciphertext
            )

    requested_events = {
        item.event_key: item
        for item in payload.events
    }

    unknown_events = (
        set(requested_events)
        - set(NOTIFICATION_EVENTS)
    )

    if unknown_events:
        raise ValueError(
            "Unsupported notification event(s): "
            + ", ".join(
                sorted(unknown_events)
            )
        )

    preferences = get_event_preferences(
        db
    )

    for preference in preferences:
        requested = requested_events.get(
            preference.event_key
        )

        if requested is None:
            continue

        preference.email_enabled = (
            requested.email_enabled
        )

        preference.discord_enabled = (
            requested.discord_enabled
        )

    db.commit()
    db.refresh(settings)

    return settings


def notification_settings_response(
    db: Session,
    settings: NotificationSettings,
) -> dict:
    recipients = []

    if settings.email_recipients:
        recipients = [
            item.strip()
            for item
            in settings.email_recipients.splitlines()
            if item.strip()
        ]

    preferences = get_event_preferences(
        db
    )

    return {
        "email_enabled":
            settings.email_enabled,

        "smtp_host":
            settings.smtp_host,

        "smtp_port":
            settings.smtp_port,

        "smtp_security":
            settings.smtp_security,

        "smtp_username":
            settings.smtp_username,

        "smtp_password_configured":
            (
                settings.smtp_password_nonce
                is not None
                and settings.smtp_password_ciphertext
                is not None
            ),

        "email_from":
            settings.email_from,

        "email_recipients":
            recipients,

        "discord_enabled":
            settings.discord_enabled,

        "discord_webhook_configured":
            (
                settings.discord_webhook_nonce
                is not None
                and settings.discord_webhook_ciphertext
                is not None
            ),

        "events": [
            {
                "event_key":
                    preference.event_key,

                "email_enabled":
                    preference.email_enabled,

                "discord_enabled":
                    preference.discord_enabled,
            }
            for preference in preferences
        ],
    }


def send_discord_message(
    db: Session,
    message: str,
) -> None:
    import json
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    from app.core.credentials import decrypt_secret

    settings = get_notification_settings(
        db
    )

    if (
        settings.discord_webhook_nonce is None
        or settings.discord_webhook_ciphertext is None
    ):
        raise ValueError(
            "Discord webhook is not configured"
        )

    webhook_url = decrypt_secret(
        settings.discord_webhook_nonce,
        settings.discord_webhook_ciphertext,
    )

    payload = json.dumps(
        {
            "content": message,
        }
    ).encode("utf-8")

    request = Request(
        webhook_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "PatchForge-for-Linux",
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=15,
        ) as response:
            status_code = response.status

    except HTTPError as exc:
        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"Discord webhook failed "
            f"with HTTP {exc.code}: "
            f"{body or exc.reason}"
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            f"Discord webhook connection failed: "
            f"{exc.reason}"
        ) from exc

    except OSError as exc:
        raise RuntimeError(
            f"Discord webhook connection failed: "
            f"{exc}"
        ) from exc

    if not 200 <= status_code < 300:
        raise RuntimeError(
            f"Discord webhook returned "
            f"HTTP {status_code}"
        )


def send_email_message(
    db: Session,
    subject: str,
    message: str,
) -> None:
    import smtplib
    import ssl
    from email.message import EmailMessage

    from app.core.credentials import decrypt_secret

    settings = get_notification_settings(
        db
    )

    if not settings.smtp_host:
        raise ValueError(
            "SMTP host is not configured"
        )

    if not settings.email_from:
        raise ValueError(
            "Email sender address is not configured"
        )

    recipients = []

    if settings.email_recipients:
        recipients = [
            item.strip()
            for item
            in settings.email_recipients.splitlines()
            if item.strip()
        ]

    if not recipients:
        raise ValueError(
            "No email recipients are configured"
        )

    smtp_password = None

    if (
        settings.smtp_password_nonce is not None
        and settings.smtp_password_ciphertext is not None
    ):
        smtp_password = decrypt_secret(
            settings.smtp_password_nonce,
            settings.smtp_password_ciphertext,
        )

    email = EmailMessage()

    email["Subject"] = subject
    email["From"] = settings.email_from
    email["To"] = ", ".join(recipients)

    email.set_content(
        message
    )

    try:
        if settings.smtp_security == "tls":
            context = ssl.create_default_context()

            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=15,
                context=context,
            ) as smtp:
                if settings.smtp_username:
                    smtp.login(
                        settings.smtp_username,
                        smtp_password or "",
                    )

                smtp.send_message(
                    email
                )

        else:
            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=15,
            ) as smtp:
                smtp.ehlo()

                if settings.smtp_security == "starttls":
                    context = ssl.create_default_context()

                    smtp.starttls(
                        context=context
                    )

                    smtp.ehlo()

                if settings.smtp_username:
                    smtp.login(
                        settings.smtp_username,
                        smtp_password or "",
                    )

                smtp.send_message(
                    email
                )

    except (
        smtplib.SMTPException,
        OSError,
    ) as exc:
        raise RuntimeError(
            f"Email delivery failed: {exc}"
        ) from exc


def delete_discord_settings(
    db: Session,
) -> NotificationSettings:
    settings = get_notification_settings(
        db
    )

    settings.discord_enabled = False
    settings.discord_webhook_nonce = None
    settings.discord_webhook_ciphertext = None

    preferences = get_event_preferences(
        db
    )

    for preference in preferences:
        preference.discord_enabled = False

    db.commit()
    db.refresh(settings)

    return settings


def delete_email_settings(
    db: Session,
) -> NotificationSettings:
    settings = get_notification_settings(
        db
    )

    settings.email_enabled = False

    settings.smtp_host = None
    settings.smtp_port = 587
    settings.smtp_security = "starttls"
    settings.smtp_username = None

    settings.smtp_password_nonce = None
    settings.smtp_password_ciphertext = None

    settings.email_from = None
    settings.email_recipients = None

    preferences = get_event_preferences(
        db
    )

    for preference in preferences:
        preference.email_enabled = False

    db.commit()
    db.refresh(settings)

    return settings


def update_discord_settings(
    db: Session,
    discord_enabled: bool,
    discord_webhook_url: str | None,
) -> NotificationSettings:
    settings = get_notification_settings(
        db
    )

    settings.discord_enabled = (
        discord_enabled
    )

    if discord_webhook_url is not None:
        webhook = discord_webhook_url.strip()

        if webhook:
            nonce, ciphertext = encrypt_secret(
                webhook
            )

            settings.discord_webhook_nonce = nonce
            settings.discord_webhook_ciphertext = (
                ciphertext
            )

    db.commit()
    db.refresh(settings)

    return settings


def update_email_settings(
    db: Session,
    email_enabled: bool,
    smtp_host: str | None,
    smtp_port: int,
    smtp_security: str,
    smtp_username: str | None,
    smtp_password: str | None,
    email_from: str | None,
    email_recipients: list[str],
) -> NotificationSettings:
    settings = get_notification_settings(
        db
    )

    settings.email_enabled = (
        email_enabled
    )

    settings.smtp_host = (
        _normalize_optional_string(
            smtp_host
        )
    )

    settings.smtp_port = smtp_port
    settings.smtp_security = smtp_security

    settings.smtp_username = (
        _normalize_optional_string(
            smtp_username
        )
    )

    settings.email_from = (
        _normalize_optional_string(
            email_from
        )
    )

    recipients = _normalize_recipients(
        email_recipients
    )

    settings.email_recipients = (
        "\n".join(recipients)
        if recipients
        else None
    )

    if smtp_password is not None:
        password = smtp_password.strip()

        if password:
            nonce, ciphertext = encrypt_secret(
                password
            )

            settings.smtp_password_nonce = nonce
            settings.smtp_password_ciphertext = (
                ciphertext
            )

    db.commit()
    db.refresh(settings)

    return settings


def update_notification_events(
    db: Session,
    events,
) -> NotificationSettings:
    settings = get_notification_settings(
        db
    )

    requested_events = {
        item.event_key: item
        for item in events
    }

    unknown_events = (
        set(requested_events)
        - set(NOTIFICATION_EVENTS)
    )

    if unknown_events:
        raise ValueError(
            "Unsupported notification event(s): "
            + ", ".join(
                sorted(unknown_events)
            )
        )

    preferences = get_event_preferences(
        db
    )

    for preference in preferences:
        requested = requested_events.get(
            preference.event_key
        )

        if requested is None:
            continue

        preference.email_enabled = (
            requested.email_enabled
        )

        preference.discord_enabled = (
            requested.discord_enabled
        )

    db.commit()
    db.refresh(settings)

    return settings


def send_discord_test_message(
    db: Session,
    message: str,
    webhook_url: str | None = None,
) -> None:
    import json
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    from app.core.credentials import decrypt_secret

    if webhook_url:
        resolved_webhook = webhook_url.strip()

    else:
        settings = get_notification_settings(
            db
        )

        if (
            settings.discord_webhook_nonce is None
            or settings.discord_webhook_ciphertext is None
        ):
            raise ValueError(
                "Discord webhook is not configured"
            )

        resolved_webhook = decrypt_secret(
            settings.discord_webhook_nonce,
            settings.discord_webhook_ciphertext,
        )

    payload = json.dumps(
        {
            "content": message,
        }
    ).encode("utf-8")

    request = Request(
        resolved_webhook,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "PatchForge-for-Linux",
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=15,
        ) as response:
            status_code = response.status

    except HTTPError as exc:
        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"Discord webhook failed "
            f"with HTTP {exc.code}: "
            f"{body or exc.reason}"
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            f"Discord webhook connection failed: "
            f"{exc.reason}"
        ) from exc

    except OSError as exc:
        raise RuntimeError(
            f"Discord webhook connection failed: "
            f"{exc}"
        ) from exc

    if not 200 <= status_code < 300:
        raise RuntimeError(
            f"Discord webhook returned HTTP {status_code}"
        )


def send_email_test_message(
    db: Session,
    subject: str,
    message: str,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_security: str | None = None,
    smtp_username: str | None = None,
    smtp_password: str | None = None,
    email_from: str | None = None,
    email_recipients: list[str] | None = None,
) -> None:
    import smtplib
    import ssl
    from email.message import EmailMessage

    from app.core.credentials import decrypt_secret

    settings = get_notification_settings(
        db
    )

    resolved_host = (
        smtp_host.strip()
        if smtp_host and smtp_host.strip()
        else settings.smtp_host
    )

    resolved_port = (
        smtp_port
        if smtp_port is not None
        else settings.smtp_port
    )

    resolved_security = (
        smtp_security
        if smtp_security is not None
        else settings.smtp_security
    )

    resolved_username = (
        smtp_username.strip()
        if smtp_username is not None
        and smtp_username.strip()
        else settings.smtp_username
    )

    resolved_from = (
        email_from.strip()
        if email_from and email_from.strip()
        else settings.email_from
    )

    if email_recipients is not None:
        resolved_recipients = _normalize_recipients(
            email_recipients
        )
    else:
        resolved_recipients = []

        if settings.email_recipients:
            resolved_recipients = [
                item.strip()
                for item
                in settings.email_recipients.splitlines()
                if item.strip()
            ]

    resolved_password = None

    if smtp_password:
        resolved_password = smtp_password

    elif (
        settings.smtp_password_nonce is not None
        and settings.smtp_password_ciphertext is not None
    ):
        resolved_password = decrypt_secret(
            settings.smtp_password_nonce,
            settings.smtp_password_ciphertext,
        )

    if not resolved_host:
        raise ValueError(
            "SMTP host is not configured"
        )

    if not resolved_from:
        raise ValueError(
            "Email sender address is not configured"
        )

    if not resolved_recipients:
        raise ValueError(
            "No email recipients are configured"
        )

    email = EmailMessage()

    email["Subject"] = subject
    email["From"] = resolved_from
    email["To"] = ", ".join(
        resolved_recipients
    )

    email.set_content(
        message
    )

    try:
        if resolved_security == "tls":
            context = ssl.create_default_context()

            with smtplib.SMTP_SSL(
                resolved_host,
                resolved_port,
                timeout=15,
                context=context,
            ) as smtp:
                if resolved_username:
                    smtp.login(
                        resolved_username,
                        resolved_password or "",
                    )

                smtp.send_message(
                    email
                )

        else:
            with smtplib.SMTP(
                resolved_host,
                resolved_port,
                timeout=15,
            ) as smtp:
                smtp.ehlo()

                if resolved_security == "starttls":
                    context = ssl.create_default_context()

                    smtp.starttls(
                        context=context
                    )

                    smtp.ehlo()

                if resolved_username:
                    smtp.login(
                        resolved_username,
                        resolved_password or "",
                    )

                smtp.send_message(
                    email
                )

    except (
        smtplib.SMTPException,
        OSError,
    ) as exc:
        raise RuntimeError(
            f"Email delivery failed: {exc}"
        ) from exc


def send_notification_event(
    db: Session,
    event_key: str,
    title: str,
    message: str,
) -> dict:
    """
    Deliver one PatchForge event through all enabled
    channels configured for that event.

    Notification delivery errors are intentionally
    isolated from the operation that triggered the event.
    """
    import logging

    logger = logging.getLogger(__name__)

    if event_key not in NOTIFICATION_EVENTS:
        raise ValueError(
            f"Unsupported notification event: {event_key}"
        )

    settings = get_notification_settings(
        db
    )

    preference = db.scalar(
        select(
            NotificationEventPreference
        ).where(
            NotificationEventPreference.event_key
            == event_key
        )
    )

    if preference is None:
        return {
            "email": False,
            "discord": False,
        }

    result = {
        "email": False,
        "discord": False,
    }

    if (
        settings.discord_enabled
        and preference.discord_enabled
    ):
        try:
            send_discord_message(
                db,
                (
                    f"🔔 **{title}**\n\n"
                    f"{message}"
                ),
            )

            result["discord"] = True

        except Exception as exc:
            logger.exception(
                "Discord notification failed "
                "for event %s: %s",
                event_key,
                exc,
            )

    if (
        settings.email_enabled
        and preference.email_enabled
    ):
        try:
            send_email_message(
                db,
                f"PatchForge - {title}",
                message,
            )

            result["email"] = True

        except Exception as exc:
            logger.exception(
                "Email notification failed "
                "for event %s: %s",
                event_key,
                exc,
            )

    return result
