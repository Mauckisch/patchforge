from datetime import datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.history import HistoryEntry
from app.models.settings import AppSettings


DEFAULT_HISTORY_RETENTION_DAYS = 7


def get_settings(
    db: Session,
) -> AppSettings:
    settings = db.get(
        AppSettings,
        1,
    )

    if settings is None:
        settings = AppSettings(
            id=1,
            history_retention_days=DEFAULT_HISTORY_RETENTION_DAYS,
        )

        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


def cleanup_history(
    db: Session,
) -> int:
    settings = get_settings(
        db
    )

    retention_days = (
        settings.history_retention_days
    )

    if retention_days is None:
        return 0

    cutoff = datetime.utcnow() - timedelta(
        days=retention_days
    )

    result = db.execute(
        delete(HistoryEntry).where(
            HistoryEntry.created_at < cutoff
        )
    )

    db.commit()

    return result.rowcount or 0
