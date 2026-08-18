from datetime import datetime

from sqlalchemy.orm import Session

from app.models.server import Server


OPERATION_IDLE = "IDLE"
OPERATION_RUNNING = "RUNNING"
OPERATION_SUCCESS = "SUCCESS"
OPERATION_FAILED = "FAILED"

OPERATION_INSTALL_SELECTED = "INSTALL_SELECTED"
OPERATION_INSTALL_ALL = "INSTALL_ALL"
OPERATION_INSTALL_HELD = "INSTALL_HELD"
OPERATION_CHECK = "CHECK"
OPERATION_CLEANUP = "CLEANUP"


class ServerOperationBusyError(Exception):
    pass


def start_server_operation(
    db: Session,
    server: Server,
    operation_type: str,
    *,
    total: int = 0,
    message: str | None = None,
) -> None:
    if server.operation_status == OPERATION_RUNNING:
        raise ServerOperationBusyError(
            f"Another operation is already running on {server.name}"
        )

    server.operation_status = OPERATION_RUNNING
    server.operation_type = operation_type
    server.operation_progress = 0
    server.operation_current = 0
    server.operation_total = max(0, total)
    server.operation_current_package = None
    server.operation_message = (
        message
        or "Operation started"
    )
    server.operation_started_at = datetime.utcnow()

    db.commit()
    db.refresh(server)


def update_server_operation(
    db: Session,
    server: Server,
    *,
    progress: int | None = None,
    current: int | None = None,
    total: int | None = None,
    current_package: str | None = None,
    message: str | None = None,
) -> None:
    if server.operation_status != OPERATION_RUNNING:
        return

    if total is not None:
        server.operation_total = max(
            0,
            total,
        )

    if current is not None:
        server.operation_current = max(
            0,
            current,
        )

    if progress is not None:
        server.operation_progress = max(
            0,
            min(
                100,
                progress,
            ),
        )

    server.operation_current_package = (
        current_package
    )

    if message is not None:
        server.operation_message = message

    db.commit()
    db.refresh(server)


def complete_server_operation(
    db: Session,
    server: Server,
    *,
    message: str = "Operation completed successfully",
) -> None:
    server.operation_status = OPERATION_SUCCESS

    if server.operation_total > 0:
        server.operation_current = (
            server.operation_total
        )

    server.operation_progress = 100
    server.operation_current_package = None
    server.operation_message = message

    db.commit()
    db.refresh(server)


def fail_server_operation(
    db: Session,
    server: Server,
    error: Exception | str,
) -> None:
    server.operation_status = OPERATION_FAILED
    server.operation_current_package = None
    server.operation_message = str(error)

    db.commit()
    db.refresh(server)


def reset_server_operation(
    db: Session,
    server: Server,
) -> None:
    server.operation_status = OPERATION_IDLE
    server.operation_type = None
    server.operation_progress = 0
    server.operation_current = 0
    server.operation_total = 0
    server.operation_current_package = None
    server.operation_message = None
    server.operation_started_at = None

    db.commit()
    db.refresh(server)


def reset_interrupted_operations(
    db: Session,
) -> int:
    servers = (
        db.query(Server)
        .filter(
            Server.operation_status
            == OPERATION_RUNNING
        )
        .all()
    )

    count = 0

    for server in servers:
        server.operation_status = OPERATION_FAILED
        server.operation_current_package = None
        server.operation_message = (
            "Operation interrupted because PatchForge restarted."
        )

        count += 1

    if count:
        db.commit()

    return count
