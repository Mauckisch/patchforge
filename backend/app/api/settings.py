from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.settings import (
    SettingsResponse,
    SettingsUpdate,
)
from app.services.settings import (
    cleanup_history,
    get_settings,
)


router = APIRouter(
    prefix="/api/settings",
    tags=["settings"],
)


@router.get(
    "",
    response_model=SettingsResponse,
)
def read_settings(
    db: Session = Depends(get_db),
) -> dict:
    settings = get_settings(
        db
    )

    return {
        "history_retention_days":
            settings.history_retention_days,
    }


@router.patch(
    "",
    response_model=SettingsResponse,
)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
) -> dict:
    settings = get_settings(
        db
    )

    settings.history_retention_days = (
        payload.history_retention_days
    )

    db.commit()
    db.refresh(settings)

    # Apply the new retention immediately.
    cleanup_history(
        db
    )

    return {
        "history_retention_days":
            settings.history_retention_days,
    }
