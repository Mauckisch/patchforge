from threading import Lock, Thread

from app.core.database import SessionLocal
from app.models.server import Server
from app.services.history import (
    ACTION_INSTALL_ALL,
    ACTION_INSTALL_SELECTED,
    STATUS_FAILED,
    STATUS_SUCCESS,
    create_history_entry,
)
from app.services.notifications import (
    EVENT_INSTALL_FAILED,
    EVENT_INSTALL_SUCCESS,
    send_notification_event,
)
from app.services.server_operation import (
    OPERATION_INSTALL_ALL,
    OPERATION_INSTALL_SELECTED,
    complete_server_operation,
    fail_server_operation,
    start_server_operation,
    update_server_operation,
)
from app.services.update_locks import (
    filter_unlocked_updates,
    get_locked_package_names,
)
from app.services.update_snapshot import (
    replace_update_snapshot,
)


_worker_lock = Lock()
_running_servers: set[int] = set()


class UpdateWorkerBusyError(Exception):
    pass


def _claim_server(server_id: int) -> None:
    with _worker_lock:
        if server_id in _running_servers:
            raise UpdateWorkerBusyError(
                "Another update operation is already running "
                "on this server"
            )

        _running_servers.add(server_id)


def _release_server(server_id: int) -> None:
    with _worker_lock:
        _running_servers.discard(server_id)


def _get_server(
    db,
    server_id: int,
) -> Server:
    server = db.get(
        Server,
        server_id,
    )

    if server is None:
        raise RuntimeError(
            f"Server {server_id} no longer exists"
        )

    return server


def _record_failure(
    db,
    server: Server,
    action: str,
    exc: Exception,
) -> None:
    fail_server_operation(
        db,
        server,
        exc,
    )

    create_history_entry(
        db=db,
        server=server,
        action=action,
        status=STATUS_FAILED,
        package_count=0,
        reboot_required=server.reboot_required,
        message=str(exc),
    )

    send_notification_event(
        db=db,
        event_key=EVENT_INSTALL_FAILED,
        title=f"Update installation failed on {server.name}",
        message=(
            f"Server: {server.name}\n"
            f"Host: {server.host}\n"
            f"Action: {action}\n"
            f"Error: {exc}"
        ),
    )


def _install_worker(
    server_id: int,
    packages: list[str] | None,
    install_all: bool,
) -> None:
    db = SessionLocal()
    transport = None

    action = (
        ACTION_INSTALL_ALL
        if install_all
        else ACTION_INSTALL_SELECTED
    )

    try:
        # Import here to avoid a module-level circular import.
        from app.api.updates import (
            _open_update_session,
        )

        server = _get_server(
            db,
            server_id,
        )

        (
            updater,
            transport,
            method,
            privilege_password,
        ) = _open_update_session(
            server,
            db,
        )

        updater.refresh_package_index(
            transport,
            method,
            privilege_password,
        )

        available_updates = updater.list_updates(
            transport
        )

        locked_packages = (
            get_locked_package_names(
                db,
                server.id,
            )
        )

        if install_all:
            available_updates = (
                filter_unlocked_updates(
                    available_updates,
                    locked_packages,
                )
            )

            package_names = [
                update["name"]
                for update in available_updates
            ]

        else:
            requested = packages or []

            requested_locked = [
                package
                for package in requested
                if package in locked_packages
            ]

            if requested_locked:
                raise RuntimeError(
                    "Locked package(s) cannot be installed: "
                    + ", ".join(requested_locked)
                )

            package_names = requested

        validated_packages = (
            updater.validate_requested_packages(
                package_names,
                available_updates,
            )
        )

        if not validated_packages:
            complete_server_operation(
                db,
                server,
                message="No updates available",
            )

            return

        # We know the real requested total at this point.
        server.operation_total = len(
            validated_packages
        )
        server.operation_message = (
            f"Installing {len(validated_packages)} update(s)"
        )

        db.commit()
        db.refresh(server)

        last_progress = -1
        last_package: str | None = None

        def handle_progress(
            progress_data: dict,
        ) -> None:
            nonlocal last_progress
            nonlocal last_package

            percent = int(
                round(
                    float(
                        progress_data.get(
                            "percent",
                            0.0,
                        )
                    )
                )
            )

            percent = max(
                0,
                min(
                    100,
                    percent,
                ),
            )

            package_name = (
                progress_data.get(
                    "package"
                )
            )

            message = (
                progress_data.get(
                    "message"
                )
                or "Installing updates"
            )

            total = len(
                validated_packages
            )

            if percent <= 0:
                current = 0

            elif percent >= 100:
                current = total

            else:
                current = min(
                    total,
                    max(
                        1,
                        int(
                            (
                                percent
                                / 100
                            )
                            * total
                        )
                        + 1,
                    ),
                )

            # Avoid a database commit for every repeated
            # APT status message. Persist whenever the
            # displayed percentage or package changes.
            if (
                percent == last_progress
                and package_name == last_package
            ):
                return

            last_progress = percent
            last_package = package_name

            update_server_operation(
                db,
                server,
                progress=percent,
                current=current,
                total=total,
                current_package=package_name,
                message=message,
            )

        updater.install_updates(
            transport,
            validated_packages,
            method,
            privilege_password,
            progress_callback=handle_progress,
        )

        remaining_all_updates = (
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

        replace_update_snapshot(
            db,
            server,
            remaining_all_updates,
            [],
            locked_packages,
        )

        remaining_updates = (
            filter_unlocked_updates(
                remaining_all_updates,
                locked_packages,
            )
        )

        reboot_status = (
            updater.get_reboot_status(
                transport
            )
        )

        server.reboot_required = (
            reboot_status["reboot_required"]
        )

        server.updates_available = len(
            remaining_updates
        )

        db.commit()
        db.refresh(server)

        create_history_entry(
            db=db,
            server=server,
            action=action,
            status=STATUS_SUCCESS,
            package_count=len(
                validated_packages
            ),
            reboot_required=server.reboot_required,
            message=(
                f"Installed {len(validated_packages)} update(s)"
            ),
        )

        send_notification_event(
            db=db,
            event_key=EVENT_INSTALL_SUCCESS,
            title=f"Updates installed on {server.name}",
            message=(
                f"Server: {server.name}\n"
                f"Host: {server.host}\n"
                f"Installed packages: "
                f"{len(validated_packages)}\n"
                f"Packages: "
                f"{', '.join(validated_packages)}"
            ),
        )

        complete_server_operation(
            db,
            server,
            message=(
                f"Installed "
                f"{len(validated_packages)} update(s)"
            ),
        )

    except Exception as exc:
        try:
            server = _get_server(
                db,
                server_id,
            )

            _record_failure(
                db,
                server,
                action,
                exc,
            )

        except Exception:
            # Nothing useful can be persisted if even the
            # server record is unavailable.
            pass

    finally:
        if transport is not None:
            transport.close()

        db.close()

        _release_server(
            server_id
        )


def start_update_worker(
    server_id: int,
    *,
    packages: list[str] | None = None,
    install_all: bool = False,
) -> None:
    _claim_server(
        server_id
    )

    db = SessionLocal()

    try:
        server = _get_server(
            db,
            server_id,
        )

        operation_type = (
            OPERATION_INSTALL_ALL
            if install_all
            else OPERATION_INSTALL_SELECTED
        )

        start_server_operation(
            db,
            server,
            operation_type,
            total=(
                0
                if install_all
                else len(packages or [])
            ),
            message=(
                "Preparing update installation"
            ),
        )

    except Exception:
        _release_server(
            server_id
        )

        raise

    finally:
        db.close()

    thread = Thread(
        target=_install_worker,
        kwargs={
            "server_id": server_id,
            "packages": packages,
            "install_all": install_all,
        },
        daemon=True,
        name=f"patchforge-update-{server_id}",
    )

    try:
        thread.start()

    except Exception:
        _release_server(
            server_id
        )

        db = SessionLocal()

        try:
            server = _get_server(
                db,
                server_id,
            )

            fail_server_operation(
                db,
                server,
                "Unable to start update worker",
            )

        finally:
            db.close()

        raise
