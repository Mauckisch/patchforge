from sqlalchemy.orm import Session

from app.models.history import HistoryEntry
from app.models.server import Server


ACTION_CHECK = "CHECK"
ACTION_INSTALL_SELECTED = "INSTALL_SELECTED"
ACTION_INSTALL_ALL = "INSTALL_ALL"
ACTION_CLEANUP = "CLEANUP"

STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"


def create_history_entry(
    db: Session,
    server: Server,
    action: str,
    status: str,
    package_count: int = 0,
    reboot_required: bool = False,
    message: str | None = None,
    task_run_id: int | None = None,
) -> HistoryEntry:
    entry = HistoryEntry(
        server_id=server.id,
        server_name=server.name,
        task_run_id=task_run_id,
        action=action,
        status=status,
        package_count=package_count,
        reboot_required=reboot_required,
        message=message,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return entry
