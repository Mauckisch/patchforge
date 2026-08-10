from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.server import Server
from app.models.server_update import (
    ServerUpdate,
)


def replace_update_snapshot(
    db: Session,
    server: Server,
    updates: list[dict],
    held_updates: list[dict] | None = None,
) -> None:
    db.execute(
        delete(ServerUpdate).where(
            ServerUpdate.server_id
            == server.id
        )
    )

    checked_at = datetime.utcnow()

    held_updates = (
        held_updates or []
    )

    for update in updates:
        db.add(
            ServerUpdate(
                server_id=server.id,
                name=update["name"],
                installed_version=(
                    update[
                        "installed_version"
                    ]
                ),
                available_version=(
                    update[
                        "available_version"
                    ]
                ),
                held=False,
                checked_at=checked_at,
            )
        )

    for update in held_updates:
        db.add(
            ServerUpdate(
                server_id=server.id,
                name=update["name"],
                installed_version=(
                    update[
                        "installed_version"
                    ]
                ),
                available_version=(
                    update[
                        "available_version"
                    ]
                ),
                held=True,
                checked_at=checked_at,
            )
        )

    # Only genuinely installable updates
    # count toward the normal update total.
    server.updates_available = len(
        updates
    )

    server.updates_checked_at = (
        checked_at
    )


def get_update_snapshot(
    db: Session,
    server_id: int,
) -> list[ServerUpdate]:
    return list(
        db.scalars(
            select(ServerUpdate)
            .where(
                ServerUpdate.server_id
                == server_id
            )
            .order_by(
                ServerUpdate.held,
                ServerUpdate.name,
            )
        ).all()
    )
