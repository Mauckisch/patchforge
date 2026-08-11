from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.notification import (
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    NotificationTestRequest,
    DiscordSettingsUpdate,
    EmailSettingsUpdate,
    NotificationChannelEnabledUpdate,
    NotificationEventsUpdate,
)
from app.services.notifications import (
    delete_discord_settings,
    delete_email_settings,
    get_notification_settings,
    notification_settings_response,
    send_discord_message,
    send_discord_test_message,
    send_email_test_message,
    send_email_message,
    update_discord_settings,
    update_email_settings,
    update_notification_channel_enabled,
    update_notification_events,
    update_notification_settings,
)


router = APIRouter(
    prefix="/api/notifications",
    tags=["notifications"],
)


@router.get(
    "/settings",
    response_model=NotificationSettingsResponse,
)
def read_notification_settings(
    db: Session = Depends(get_db),
) -> dict:
    settings = get_notification_settings(
        db
    )

    return notification_settings_response(
        db,
        settings,
    )


@router.patch(
    "/settings",
    response_model=NotificationSettingsResponse,
)
def patch_notification_settings(
    payload: NotificationSettingsUpdate,
    db: Session = Depends(get_db),
) -> dict:
    try:
        settings = update_notification_settings(
            db,
            payload,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return notification_settings_response(
        db,
        settings,
    )


@router.post("/test")
def test_notification(
    payload: NotificationTestRequest,
    db: Session = Depends(get_db),
) -> dict:
    if payload.channel == "discord":
        try:
            send_discord_test_message(
                db,
                (
                    "🔔 **PatchForge for Linux**\n\n"
                    "Discord notifications are configured correctly.\n\n"
                    "This is a test notification from PatchForge."
                ),
                webhook_url=payload.discord_webhook_url,
            )

        except (
            ValueError,
            RuntimeError,
        ) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        return {
            "channel": "discord",
            "success": True,
        }

    if payload.channel == "email":
        try:
            send_email_test_message(
                db,
                "PatchForge for Linux - Test Notification",
                (
                    "PatchForge for Linux\n\n"
                    "Email notifications are configured correctly.\n\n"
                    "This is a test notification from PatchForge."
                ),
                smtp_host=payload.smtp_host,
                smtp_port=payload.smtp_port,
                smtp_security=payload.smtp_security,
                smtp_username=payload.smtp_username,
                smtp_password=payload.smtp_password,
                email_from=payload.email_from,
                email_recipients=payload.email_recipients,
            )

        except (
            ValueError,
            RuntimeError,
        ) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        return {
            "channel": "email",
            "success": True,
        }

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            f"Notification test channel "
            f"'{payload.channel}' is not implemented yet"
        ),
    )


@router.delete(
    "/settings/discord",
    response_model=NotificationSettingsResponse,
)
def delete_discord_configuration(
    db: Session = Depends(get_db),
) -> dict:
    settings = delete_discord_settings(
        db
    )

    return notification_settings_response(
        db,
        settings,
    )


@router.delete(
    "/settings/email",
    response_model=NotificationSettingsResponse,
)
def delete_email_configuration(
    db: Session = Depends(get_db),
) -> dict:
    settings = delete_email_settings(
        db
    )

    return notification_settings_response(
        db,
        settings,
    )


@router.patch(
    "/settings/discord",
    response_model=NotificationSettingsResponse,
)
def patch_discord_settings(
    payload: DiscordSettingsUpdate,
    db: Session = Depends(get_db),
) -> dict:
    settings = update_discord_settings(
        db=db,
        discord_enabled=payload.discord_enabled,
        discord_webhook_url=(
            payload.discord_webhook_url
        ),
    )

    return notification_settings_response(
        db,
        settings,
    )


@router.patch(
    "/settings/email",
    response_model=NotificationSettingsResponse,
)
def patch_email_settings(
    payload: EmailSettingsUpdate,
    db: Session = Depends(get_db),
) -> dict:
    settings = update_email_settings(
        db=db,
        email_enabled=payload.email_enabled,
        smtp_host=payload.smtp_host,
        smtp_port=payload.smtp_port,
        smtp_security=payload.smtp_security,
        smtp_username=payload.smtp_username,
        smtp_password=payload.smtp_password,
        email_from=payload.email_from,
        email_recipients=(
            payload.email_recipients
        ),
    )

    return notification_settings_response(
        db,
        settings,
    )


@router.patch(
    "/settings/discord/enabled",
    response_model=NotificationSettingsResponse,
)
def patch_discord_enabled(
    payload: NotificationChannelEnabledUpdate,
    db: Session = Depends(get_db),
) -> dict:
    settings = update_notification_channel_enabled(
        db=db,
        channel="discord",
        enabled=payload.enabled,
    )

    return notification_settings_response(
        db,
        settings,
    )


@router.patch(
    "/settings/email/enabled",
    response_model=NotificationSettingsResponse,
)
def patch_email_enabled(
    payload: NotificationChannelEnabledUpdate,
    db: Session = Depends(get_db),
) -> dict:
    settings = update_notification_channel_enabled(
        db=db,
        channel="email",
        enabled=payload.enabled,
    )

    return notification_settings_response(
        db,
        settings,
    )


@router.patch(
    "/settings/events",
    response_model=NotificationSettingsResponse,
)
def patch_notification_events(
    payload: NotificationEventsUpdate,
    db: Session = Depends(get_db),
) -> dict:
    try:
        settings = update_notification_events(
            db,
            payload.events,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return notification_settings_response(
        db,
        settings,
    )
