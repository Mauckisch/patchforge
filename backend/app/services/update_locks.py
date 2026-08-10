from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.server import Server
from app.models.server_update import ServerUpdate
from app.models.server_update_lock import (
    ServerUpdateLock,
)


def get_locked_package_names(
    db: Session,
    server_id: int,
) -> set[str]:
    return set(
        db.scalars(
            select(
                ServerUpdateLock.package_name
            ).where(
                ServerUpdateLock.server_id
                == server_id
            )
        ).all()
    )


def is_package_locked(
    db: Session,
    server_id: int,
    package_name: str,
) -> bool:
    return (
        db.scalar(
            select(
                ServerUpdateLock.id
            )
            .where(
                ServerUpdateLock.server_id
                == server_id
            )
            .where(
                ServerUpdateLock.package_name
                == package_name
            )
            .limit(1)
        )
        is not None
    )


def lock_package(
    db: Session,
    server_id: int,
    package_name: str,
) -> ServerUpdateLock:
    existing = db.scalar(
        select(
            ServerUpdateLock
        )
        .where(
            ServerUpdateLock.server_id
            == server_id
        )
        .where(
            ServerUpdateLock.package_name
            == package_name
        )
    )

    if existing is not None:
        return existing

    lock = ServerUpdateLock(
        server_id=server_id,
        package_name=package_name,
    )

    db.add(lock)

    return lock


def unlock_package(
    db: Session,
    server_id: int,
    package_name: str,
) -> None:
    db.execute(
        delete(
            ServerUpdateLock
        )
        .where(
            ServerUpdateLock.server_id
            == server_id
        )
        .where(
            ServerUpdateLock.package_name
            == package_name
        )
    )


def filter_unlocked_updates(
    updates: list[dict],
    locked_packages: set[str],
) -> list[dict]:
    return [
        update
        for update in updates
        if update["name"]
        not in locked_packages
    ]


def update_server_actionable_count(
    db: Session,
    server: Server,
) -> None:
    db.flush()

    locked_packages = (
        get_locked_package_names(
            db,
            server.id,
        )
    )

    saved_updates = list(
        db.scalars(
            select(ServerUpdate).where(
                ServerUpdate.server_id
                == server.id
            )
        ).all()
    )

    server.updates_available = sum(
        1
        for update in saved_updates
        if (
            not update.held
            and update.name
            not in locked_packages
        )
    )
