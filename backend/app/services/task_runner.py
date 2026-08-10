from datetime import datetime

from sqlalchemy import select

from app.core.credentials import decrypt_secret
from app.core.database import SessionLocal
from app.models.credential import ServerCredential
from app.models.server import Server
from app.models.task import ScheduledTask
from app.models.task_target import ScheduledTaskTarget
from app.services.history import (
    ACTION_CHECK,
    ACTION_CLEANUP,
    ACTION_INSTALL_ALL,
    STATUS_FAILED,
    STATUS_SUCCESS,
    create_history_entry,
)
from app.services.update_locks import (
    filter_unlocked_updates,
    get_locked_package_names,
)
from app.services.privilege import (
    _open_transport,
    detect_privilege_method,
)
from app.updaters.registry import get_updater


ACTION_REBOOT_CHECK = "REBOOT_CHECK"


def _get_target_ids(
    db,
    task: ScheduledTask,
) -> list[int]:
    target_ids = list(
        db.scalars(
            select(
                ScheduledTaskTarget.server_id
            ).where(
                ScheduledTaskTarget.task_id == task.id
            )
        ).all()
    )

    if not target_ids and task.server_id:
        target_ids = [
            task.server_id
        ]

    return target_ids


def _load_credentials(
    db,
    server_id: int,
):
    credential = db.scalar(
        select(ServerCredential).where(
            ServerCredential.server_id == server_id
        )
    )

    if credential is None:
        raise RuntimeError(
            "No credentials configured"
        )

    ssh_password = decrypt_secret(
        credential.ssh_password_nonce,
        credential.ssh_password_ciphertext,
    )

    privilege_password = None

    if (
        credential.privilege_password_nonce is not None
        and credential.privilege_password_ciphertext is not None
    ):
        privilege_password = decrypt_secret(
            credential.privilege_password_nonce,
            credential.privilege_password_ciphertext,
        )

    return (
        credential.privilege_method,
        ssh_password,
        privilege_password,
    )


def _resolve_privilege(
    server: Server,
    configured_method: str,
    ssh_password: str,
    separate_privilege_password: str | None,
):
    result = detect_privilege_method(
        host=server.host,
        port=server.ssh_port,
        username=server.username,
        ssh_password=ssh_password,
        configured_method=configured_method,
        privilege_password=separate_privilege_password,
    )

    method = result["method"]

    if method == "sudo":
        password = (
            separate_privilege_password
            if separate_privilege_password is not None
            else ssh_password
        )
    else:
        password = separate_privilege_password

    return method, password


def _run_for_server(
    db,
    task: ScheduledTask,
    server: Server,
) -> None:

    (
        configured_method,
        ssh_password,
        separate_privilege_password,
    ) = _load_credentials(
        db,
        server.id,
    )

    method, privilege_password = _resolve_privilege(
        server,
        configured_method,
        ssh_password,
        separate_privilege_password,
    )

    updater = get_updater(
        server.package_manager
    )

    transport = _open_transport(
        host=server.host,
        port=server.ssh_port,
        username=server.username,
        password=ssh_password,
    )

    try:
        if task.action == "CHECK":
            updater.refresh_package_index(
                transport,
                method,
                privilege_password,
            )

            updates = updater.list_updates(
                transport
            )

            reboot_status = updater.get_reboot_status(
                transport
            )

            server.reboot_required = (
                reboot_status["reboot_required"]
            )

            create_history_entry(
                db=db,
                server=server,
                action=ACTION_CHECK,
                status=STATUS_SUCCESS,
                package_count=len(updates),
                reboot_required=server.reboot_required,
                message=(
                    f"Scheduled check: "
                    f"{len(updates)} update(s) available"
                ),
            )

        elif task.action == "INSTALL_ALL":
            updater.refresh_package_index(
                transport,
                method,
                privilege_password,
            )

            updates = updater.list_updates(
                transport
            )

            locked_packages = (
                get_locked_package_names(
                    db,
                    server.id,
                )
            )

            updates = (
                filter_unlocked_updates(
                    updates,
                    locked_packages,
                )
            )

            installed_count = 0

            if updates:
                package_names = [
                    update["name"]
                    for update in updates
                ]

                validated = (
                    updater.validate_requested_packages(
                        package_names,
                        updates,
                    )
                )

                updater.install_updates(
                    transport,
                    validated,
                    method,
                    privilege_password,
                )

                installed_count = len(
                    validated
                )

            reboot_status = updater.get_reboot_status(
                transport
            )

            server.reboot_required = (
                reboot_status["reboot_required"]
            )

            create_history_entry(
                db=db,
                server=server,
                action=ACTION_INSTALL_ALL,
                status=STATUS_SUCCESS,
                package_count=installed_count,
                reboot_required=server.reboot_required,
                message=(
                    f"Scheduled install-all: "
                    f"{installed_count} update(s) installed"
                ),
            )

        elif task.action == "CLEANUP":
            updater.cleanup(
                transport,
                method,
                privilege_password,
            )

            reboot_status = updater.get_reboot_status(
                transport
            )

            server.reboot_required = (
                reboot_status["reboot_required"]
            )

            create_history_entry(
                db=db,
                server=server,
                action=ACTION_CLEANUP,
                status=STATUS_SUCCESS,
                package_count=0,
                reboot_required=server.reboot_required,
                message="Scheduled cleanup completed",
            )

        elif task.action == "REBOOT_CHECK":
            reboot_status = updater.get_reboot_status(
                transport
            )

            server.reboot_required = (
                reboot_status["reboot_required"]
            )

            create_history_entry(
                db=db,
                server=server,
                action=ACTION_REBOOT_CHECK,
                status=STATUS_SUCCESS,
                package_count=0,
                reboot_required=server.reboot_required,
                message="Scheduled reboot check completed",
            )

        else:
            raise RuntimeError(
                f"Unsupported task action: {task.action}"
            )

    finally:
        transport.close()


def run_scheduled_task(
    task_id: int,
) -> None:
    db = SessionLocal()

    try:
        task = db.get(
            ScheduledTask,
            task_id,
        )

        if task is None or not task.enabled:
            return

        target_ids = _get_target_ids(
            db,
            task,
        )

        for server_id in target_ids:
            server = db.get(
                Server,
                server_id,
            )

            if server is None:
                continue

            try:
                _run_for_server(
                    db,
                    task,
                    server,
                )

            except Exception as exc:
                db.rollback()

                server = db.get(
                    Server,
                    server_id,
                )

                if server is not None:
                    create_history_entry(
                        db=db,
                        server=server,
                        action=task.action,
                        status=STATUS_FAILED,
                        package_count=0,
                        reboot_required=server.reboot_required,
                        message=(
                            f"Scheduled task failed: {exc}"
                        ),
                    )

        task = db.get(
            ScheduledTask,
            task_id,
        )

        if task is not None:
            task.last_run_at = datetime.utcnow()

            if task.schedule_type == "once":
                task.enabled = False
                task.next_run_at = None

            db.commit()

    finally:
        db.close()
