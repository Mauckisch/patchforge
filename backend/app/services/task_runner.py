import json
from datetime import datetime

from sqlalchemy import select

from app.core.credentials import decrypt_secret
from app.core.database import SessionLocal
from app.models.credential import ServerCredential
from app.models.server import Server
from app.models.task import ScheduledTask
from app.models.task_run import (
    TaskRun,
    TaskRunResult,
)
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
from app.services.notifications import (
    EVENT_TASK_FAILED,
    EVENT_TASK_SUCCESS,
    send_notification_event,
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
    task_run_id: int,
) -> dict:
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

            cleanup_available = (
                updater.cleanup_available(
                    transport
                )
            )

            reboot_status = updater.get_reboot_status(
                transport
            )

            update_names = [
                str(update["name"])
                for update in updates
            ]

            server.updates_available = len(
                updates
            )

            server.cleanup_available = (
                cleanup_available
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
                task_run_id=task_run_id,
                message=(
                    f"Scheduled check: "
                    f"{len(updates)} update(s) available"
                ),
            )

            return {
                "update_count": len(updates),
                "updates": update_names,
                "installed_count": 0,
                "installed_packages": [],
                "remaining_updates": len(updates),
                "cleanup_available":
                    cleanup_available,
                "reboot_required":
                    server.reboot_required,
            }

        if task.action == "INSTALL_ALL":
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

            validated: list[str] = []

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

            remaining_updates = (
                updater.list_updates(
                    transport
                )
            )

            locked_packages = (
                get_locked_package_names(
                    db,
                    server.id,
                )
            )

            remaining_updates = (
                filter_unlocked_updates(
                    remaining_updates,
                    locked_packages,
                )
            )

            cleanup_available = (
                updater.cleanup_available(
                    transport
                )
            )

            reboot_status = updater.get_reboot_status(
                transport
            )

            server.updates_available = len(
                remaining_updates
            )

            server.cleanup_available = (
                cleanup_available
            )

            server.reboot_required = (
                reboot_status["reboot_required"]
            )

            create_history_entry(
                db=db,
                server=server,
                action=ACTION_INSTALL_ALL,
                status=STATUS_SUCCESS,
                package_count=len(validated),
                reboot_required=server.reboot_required,
                task_run_id=task_run_id,
                message=(
                    f"Scheduled install-all: "
                    f"{len(validated)} update(s) installed"
                ),
            )

            return {
                "update_count": 0,
                "updates": [],
                "installed_count": len(validated),
                "installed_packages": [
                    str(package)
                    for package in validated
                ],
                "remaining_updates":
                    len(remaining_updates),
                "cleanup_available":
                    cleanup_available,
                "reboot_required":
                    server.reboot_required,
            }

        if task.action == "CLEANUP":
            updater.cleanup(
                transport,
                method,
                privilege_password,
            )

            remaining_updates = (
                updater.list_updates(
                    transport
                )
            )

            locked_packages = (
                get_locked_package_names(
                    db,
                    server.id,
                )
            )

            remaining_updates = (
                filter_unlocked_updates(
                    remaining_updates,
                    locked_packages,
                )
            )

            cleanup_available = (
                updater.cleanup_available(
                    transport
                )
            )

            reboot_status = updater.get_reboot_status(
                transport
            )

            server.updates_available = len(
                remaining_updates
            )

            server.cleanup_available = (
                cleanup_available
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
                task_run_id=task_run_id,
                message="Scheduled cleanup completed",
            )

            return {
                "update_count": 0,
                "updates": [],
                "installed_count": 0,
                "installed_packages": [],
                "remaining_updates":
                    len(remaining_updates),
                "cleanup_available":
                    cleanup_available,
                "reboot_required":
                    server.reboot_required,
            }

        if task.action == "REBOOT_CHECK":
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
                task_run_id=task_run_id,
                message="Scheduled reboot check completed",
            )

            return {
                "update_count": 0,
                "updates": [],
                "installed_count": 0,
                "installed_packages": [],
                "remaining_updates": 0,
                "cleanup_available":
                    server.cleanup_available,
                "reboot_required":
                    server.reboot_required,
            }

        raise RuntimeError(
            f"Unsupported task action: {task.action}"
        )

    finally:
        transport.close()


def _package_summary(
    packages: list[str],
    limit: int = 10,
) -> str:
    if not packages:
        return ""

    shown = packages[:limit]

    result = ", ".join(
        shown
    )

    remaining = len(packages) - len(shown)

    if remaining > 0:
        result += (
            f", +{remaining} more"
        )

    return result


def _format_task_run_notification(
    task: ScheduledTask,
    target_count: int,
    success_count: int,
    failed_count: int,
    successful_results: list[dict],
    failed_results: list[dict],
) -> str:
    lines = [
        f"Action: {task.action}",
        f"Targets: {target_count}",
        f"Successful: {success_count}",
        f"Failed: {failed_count}",
    ]

    if task.action == "CHECK":
        total_updates = sum(
            result["update_count"]
            for result in successful_results
        )

        lines.append(
            f"Updates found: {total_updates}"
        )

        update_results = [
            result
            for result in successful_results
            if result["update_count"] > 0
        ]

        if update_results:
            lines.append("")
            lines.append("Updates:")

            for result in update_results:
                packages = _package_summary(
                    result["updates"]
                )

                lines.append(
                    f"- {result['server_name']} "
                    f"({result['host']}): "
                    f"{result['update_count']}"
                )

                if packages:
                    lines.append(
                        f"  {packages}"
                    )

    elif task.action == "INSTALL_ALL":
        installed_total = sum(
            result["installed_count"]
            for result in successful_results
        )

        reboot_count = sum(
            1
            for result in successful_results
            if result["reboot_required"]
        )

        lines.append(
            f"Installed packages: {installed_total}"
        )

        lines.append(
            f"Reboot required: {reboot_count}"
        )

        install_results = [
            result
            for result in successful_results
            if (
                result["installed_count"] > 0
                or result["reboot_required"]
            )
        ]

        if install_results:
            lines.append("")
            lines.append("Results:")

            for result in install_results:
                lines.append(
                    f"- {result['server_name']} "
                    f"({result['host']})"
                )

                lines.append(
                    f"  Installed: "
                    f"{result['installed_count']}"
                )

                if result["installed_packages"]:
                    lines.append(
                        "  Packages: "
                        + _package_summary(
                            result[
                                "installed_packages"
                            ]
                        )
                    )

                lines.append(
                    "  Reboot required: "
                    + (
                        "Yes"
                        if result["reboot_required"]
                        else "No"
                    )
                )

    elif task.action == "CLEANUP":
        reboot_count = sum(
            1
            for result in successful_results
            if result["reboot_required"]
        )

        lines.append(
            f"Reboot required: {reboot_count}"
        )

    elif task.action == "REBOOT_CHECK":
        reboot_results = [
            result
            for result in successful_results
            if result["reboot_required"]
        ]

        lines.append(
            f"Reboot required: {len(reboot_results)}"
        )

        if reboot_results:
            lines.append("")
            lines.append("Servers:")

            for result in reboot_results:
                lines.append(
                    f"- {result['server_name']} "
                    f"({result['host']})"
                )

    if failed_results:
        lines.append("")
        lines.append("Failed:")

        for result in failed_results:
            lines.append(
                f"- {result['server_name']} "
                f"({result['host']}): "
                f"{result['error']}"
            )

    message = "\n".join(
        lines
    )

    # Discord messages have a strict content size.
    # Complete details remain available in TaskRunResult.
    if len(message) > 1800:
        message = (
            message[:1750]
            + "\n\n… additional details are available "
            "in the PatchForge task run."
        )

    return message


def run_scheduled_task(
    task_id: int,
    force: bool = False,
) -> None:
    db = SessionLocal()

    try:
        task = db.get(
            ScheduledTask,
            task_id,
        )

        if task is None:
            return

        if not task.enabled and not force:
            return

        target_ids = _get_target_ids(
            db,
            task,
        )

        run = TaskRun(
            task_id=task.id,
            task_name=task.name,
            action=task.action,
            status="RUNNING",
            target_count=len(target_ids),
            success_count=0,
            failed_count=0,
            updates_found=0,
        )

        db.add(run)
        db.commit()
        db.refresh(run)

        run_id = run.id

        successful_results: list[dict] = []
        failed_results: list[dict] = []

        for server_id in target_ids:
            server = db.get(
                Server,
                server_id,
            )

            if server is None:
                failed_result = {
                    "server_id": server_id,
                    "server_name":
                        f"Server {server_id}",
                    "host": "unknown",
                    "error":
                        "Managed server no longer exists",
                }

                failed_results.append(
                    failed_result
                )

                db.add(
                    TaskRunResult(
                        run_id=run_id,
                        server_id=server_id,
                        server_name=(
                            failed_result[
                                "server_name"
                            ]
                        ),
                        host="unknown",
                        status="FAILED",
                        update_count=0,
                        updates_json=None,
                        installed_count=0,
                        installed_packages_json=None,
                        remaining_updates=0,
                        cleanup_available=None,
                        reboot_required=False,
                        error=failed_result["error"],
                    )
                )

                db.commit()
                continue

            server_name = server.name
            server_host = server.host

            try:
                result = _run_for_server(
                    db,
                    task,
                    server,
                    run_id,
                )

                successful_result = {
                    "server_id": server.id,
                    "server_name": server_name,
                    "host": server_host,
                    **result,
                }

                successful_results.append(
                    successful_result
                )

                db.add(
                    TaskRunResult(
                        run_id=run_id,
                        server_id=server.id,
                        server_name=server_name,
                        host=server_host,
                        status="SUCCESS",
                        update_count=(
                            result["update_count"]
                        ),
                        updates_json=(
                            json.dumps(
                                result["updates"]
                            )
                            if result["updates"]
                            else None
                        ),
                        installed_count=(
                            result[
                                "installed_count"
                            ]
                        ),
                        installed_packages_json=(
                            json.dumps(
                                result[
                                    "installed_packages"
                                ]
                            )
                            if result[
                                "installed_packages"
                            ]
                            else None
                        ),
                        remaining_updates=(
                            result[
                                "remaining_updates"
                            ]
                        ),
                        cleanup_available=(
                            result[
                                "cleanup_available"
                            ]
                        ),
                        reboot_required=(
                            result[
                                "reboot_required"
                            ]
                        ),
                        error=None,
                    )
                )

                db.commit()

            except Exception as exc:
                db.rollback()

                server = db.get(
                    Server,
                    server_id,
                )

                reboot_required = False

                if server is not None:
                    reboot_required = (
                        server.reboot_required
                    )

                    create_history_entry(
                        db=db,
                        server=server,
                        action=task.action,
                        status=STATUS_FAILED,
                        package_count=0,
                        reboot_required=(
                            reboot_required
                        ),
                        task_run_id=run_id,
                        message=(
                            "Scheduled task failed: "
                            f"{exc}"
                        ),
                    )

                failed_result = {
                    "server_id": server_id,
                    "server_name": server_name,
                    "host": server_host,
                    "error": str(exc),
                }

                failed_results.append(
                    failed_result
                )

                db.add(
                    TaskRunResult(
                        run_id=run_id,
                        server_id=server_id,
                        server_name=server_name,
                        host=server_host,
                        status="FAILED",
                        update_count=0,
                        updates_json=None,
                        installed_count=0,
                        installed_packages_json=None,
                        remaining_updates=0,
                        cleanup_available=None,
                        reboot_required=(
                            reboot_required
                        ),
                        error=str(exc),
                    )
                )

                db.commit()

        success_count = len(
            successful_results
        )

        failed_count = len(
            failed_results
        )

        updates_found = sum(
            result["update_count"]
            for result in successful_results
        )

        run = db.get(
            TaskRun,
            run_id,
        )

        if run is not None:
            run.success_count = success_count
            run.failed_count = failed_count
            run.updates_found = updates_found
            run.completed_at = datetime.utcnow()

            if failed_count == 0:
                run.status = "SUCCESS"

            elif success_count == 0:
                run.status = "FAILED"

            else:
                run.status = "PARTIAL"

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

        if task is None:
            return

        suppress_notification = (
            task.action == "CHECK"
            and task.notify_only_on_updates
            and updates_found == 0
        )

        if suppress_notification:
            return

        message = _format_task_run_notification(
            task=task,
            target_count=len(target_ids),
            success_count=success_count,
            failed_count=failed_count,
            successful_results=successful_results,
            failed_results=failed_results,
        )

        if failed_count > 0:
            send_notification_event(
                db=db,
                event_key=EVENT_TASK_FAILED,
                title=task.name,
                message=message,
            )

        else:
            send_notification_event(
                db=db,
                event_key=EVENT_TASK_SUCCESS,
                title=task.name,
                message=message,
            )

    finally:
        db.close()
