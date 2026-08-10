from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.credentials import decrypt_secret
from app.core.dependencies import get_db
from app.models.credential import ServerCredential
from app.models.server import Server
from app.schemas.update import InstallUpdatesRequest
from app.services.discovery import AuthenticationError, DiscoveryError
from app.services.history import (
    ACTION_CHECK,
    ACTION_CLEANUP,
    ACTION_INSTALL_ALL,
    ACTION_INSTALL_SELECTED,
    STATUS_FAILED,
    STATUS_SUCCESS,
    create_history_entry,
)
from app.services.privilege import (
    PrivilegeError,
    PrivilegeUnavailableError,
    _open_transport,
    detect_privilege_method,
)
from app.updaters.base import UpdaterError
from app.updaters.registry import get_updater


router = APIRouter(
    prefix="/api/servers",
    tags=["updates"],
)


def _load_credentials(
    server_id: int,
    db: Session,
) -> tuple[ServerCredential, str, str | None]:
    credential = db.scalar(
        select(ServerCredential).where(
            ServerCredential.server_id == server_id
        )
    )

    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No credentials configured",
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

    return credential, ssh_password, privilege_password


def _resolve_privilege(
    server: Server,
    credential: ServerCredential,
    ssh_password: str,
    separate_privilege_password: str | None,
) -> tuple[str, str | None]:
    privilege = detect_privilege_method(
        host=server.host,
        port=server.ssh_port,
        username=server.username,
        ssh_password=ssh_password,
        configured_method=credential.privilege_method,
        privilege_password=separate_privilege_password,
    )

    method = privilege["method"]

    if method == "sudo":
        password = (
            separate_privilege_password
            if separate_privilege_password is not None
            else ssh_password
        )
    else:
        password = separate_privilege_password

    return method, password


def _log_failure(
    db: Session,
    server: Server,
    action: str,
    exc: Exception,
) -> None:
    create_history_entry(
        db=db,
        server=server,
        action=action,
        status=STATUS_FAILED,
        package_count=0,
        reboot_required=server.reboot_required,
        message=str(exc),
    )


def _get_server(
    server_id: int,
    db: Session,
) -> Server:
    server = db.get(Server, server_id)

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    return server


def _open_update_session(
    server: Server,
    db: Session,
) -> tuple:
    credential, ssh_password, separate_password = (
        _load_credentials(
            server.id,
            db,
        )
    )

    method, privilege_password = _resolve_privilege(
        server,
        credential,
        ssh_password,
        separate_password,
    )

    transport = _open_transport(
        host=server.host,
        port=server.ssh_port,
        username=server.username,
        password=ssh_password,
    )

    updater = get_updater(
        server.package_manager
    )

    return (
        updater,
        transport,
        method,
        privilege_password,
    )


def _raise_update_error(
    db: Session,
    server: Server,
    action: str,
    exc: Exception,
) -> None:
    _log_failure(
        db,
        server,
        action,
        exc,
    )

    if isinstance(
        exc,
        AuthenticationError,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    if isinstance(
        exc,
        (
            PrivilegeUnavailableError,
            UpdaterError,
        ),
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=str(exc),
    ) from exc


@router.post("/{server_id}/updates/check")
def check_updates(
    server_id: int,
    db: Session = Depends(get_db),
) -> dict:
    server = _get_server(
        server_id,
        db,
    )

    try:
        (
            updater,
            transport,
            method,
            privilege_password,
        ) = _open_update_session(
            server,
            db,
        )

        try:
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

        finally:
            transport.close()

        server.reboot_required = (
            reboot_status["reboot_required"]
        )

        server.updates_available = len(
            updates
        )

        from app.services.server_status import mark_online
        mark_online(server)

        db.commit()
        db.refresh(server)

        create_history_entry(
            db=db,
            server=server,
            action=ACTION_CHECK,
            status=STATUS_SUCCESS,
            package_count=len(updates),
            reboot_required=server.reboot_required,
            message=f"{len(updates)} update(s) available",
        )

        return {
            "server_id": server.id,
            "server": server.name,
            "system_hostname": server.system_hostname,
            "package_manager": server.package_manager,
            "updates_available": len(updates),
            "reboot_required": server.reboot_required,
            "updates": updates,
        }

    except (
        AuthenticationError,
        PrivilegeUnavailableError,
        PrivilegeError,
        DiscoveryError,
        UpdaterError,
    ) as exc:
        _raise_update_error(
            db,
            server,
            ACTION_CHECK,
            exc,
        )


@router.post("/{server_id}/updates/install")
def install_selected_updates(
    server_id: int,
    payload: InstallUpdatesRequest,
    db: Session = Depends(get_db),
) -> dict:
    server = _get_server(
        server_id,
        db,
    )

    try:
        (
            updater,
            transport,
            method,
            privilege_password,
        ) = _open_update_session(
            server,
            db,
        )

        try:
            updater.refresh_package_index(
                transport,
                method,
                privilege_password,
            )

            available_updates = updater.list_updates(
                transport
            )

            validated_packages = (
                updater.validate_requested_packages(
                    payload.packages,
                    available_updates,
                )
            )

            updater.install_updates(
                transport,
                validated_packages,
                method,
                privilege_password,
            )

            remaining_updates = updater.list_updates(
                transport
            )

            reboot_status = updater.get_reboot_status(
                transport
            )

        finally:
            transport.close()

        server.reboot_required = (
            reboot_status["reboot_required"]
        )

        db.commit()
        db.refresh(server)

        create_history_entry(
            db=db,
            server=server,
            action=ACTION_INSTALL_SELECTED,
            status=STATUS_SUCCESS,
            package_count=len(validated_packages),
            reboot_required=server.reboot_required,
            message=(
                f"Installed: {', '.join(validated_packages)}"
            ),
        )

        return {
            "server_id": server.id,
            "server": server.name,
            "system_hostname": server.system_hostname,
            "installed_packages": validated_packages,
            "remaining_updates": len(remaining_updates),
            "reboot_required": server.reboot_required,
            "updates": remaining_updates,
        }

    except (
        AuthenticationError,
        PrivilegeUnavailableError,
        PrivilegeError,
        DiscoveryError,
        UpdaterError,
    ) as exc:
        _raise_update_error(
            db,
            server,
            ACTION_INSTALL_SELECTED,
            exc,
        )


@router.post("/{server_id}/updates/install-all")
def install_all_updates(
    server_id: int,
    db: Session = Depends(get_db),
) -> dict:
    server = _get_server(
        server_id,
        db,
    )

    try:
        (
            updater,
            transport,
            method,
            privilege_password,
        ) = _open_update_session(
            server,
            db,
        )

        try:
            updater.refresh_package_index(
                transport,
                method,
                privilege_password,
            )

            available_updates = updater.list_updates(
                transport
            )

            if not available_updates:
                reboot_status = updater.get_reboot_status(
                    transport
                )

                server.reboot_required = (
                    reboot_status["reboot_required"]
                )

                db.commit()
                db.refresh(server)

                create_history_entry(
                    db=db,
                    server=server,
                    action=ACTION_INSTALL_ALL,
                    status=STATUS_SUCCESS,
                    package_count=0,
                    reboot_required=server.reboot_required,
                    message="No updates available",
                )

                return {
                    "server_id": server.id,
                    "server": server.name,
                    "system_hostname": server.system_hostname,
                    "installed_packages": [],
                    "installed_count": 0,
                    "remaining_updates": 0,
                    "reboot_required": server.reboot_required,
                    "message": "No updates available",
                }

            package_names = [
                update["name"]
                for update in available_updates
            ]

            validated_packages = (
                updater.validate_requested_packages(
                    package_names,
                    available_updates,
                )
            )

            updater.install_updates(
                transport,
                validated_packages,
                method,
                privilege_password,
            )

            remaining_updates = updater.list_updates(
                transport
            )

            reboot_status = updater.get_reboot_status(
                transport
            )

        finally:
            transport.close()

        server.reboot_required = (
            reboot_status["reboot_required"]
        )

        db.commit()
        db.refresh(server)

        create_history_entry(
            db=db,
            server=server,
            action=ACTION_INSTALL_ALL,
            status=STATUS_SUCCESS,
            package_count=len(validated_packages),
            reboot_required=server.reboot_required,
            message=(
                f"Installed {len(validated_packages)} update(s)"
            ),
        )

        return {
            "server_id": server.id,
            "server": server.name,
            "system_hostname": server.system_hostname,
            "installed_packages": validated_packages,
            "installed_count": len(validated_packages),
            "remaining_updates": len(remaining_updates),
            "reboot_required": server.reboot_required,
            "updates": remaining_updates,
        }

    except (
        AuthenticationError,
        PrivilegeUnavailableError,
        PrivilegeError,
        DiscoveryError,
        UpdaterError,
    ) as exc:
        _raise_update_error(
            db,
            server,
            ACTION_INSTALL_ALL,
            exc,
        )


@router.get("/{server_id}/reboot-status")
def get_reboot_status(
    server_id: int,
    db: Session = Depends(get_db),
) -> dict:
    server = _get_server(
        server_id,
        db,
    )

    try:
        credential, ssh_password, _ = (
            _load_credentials(
                server.id,
                db,
            )
        )

        transport = _open_transport(
            host=server.host,
            port=server.ssh_port,
            username=server.username,
            password=ssh_password,
        )

        updater = get_updater(
            server.package_manager
        )

        try:
            reboot_status = updater.get_reboot_status(
                transport
            )

        finally:
            transport.close()

        server.reboot_required = (
            reboot_status["reboot_required"]
        )

        db.commit()
        db.refresh(server)

        return {
            "server_id": server.id,
            "server": server.name,
            "system_hostname": server.system_hostname,
            **reboot_status,
        }

    except (
        AuthenticationError,
        DiscoveryError,
        UpdaterError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/{server_id}/cleanup")
def cleanup_server(
    server_id: int,
    db: Session = Depends(get_db),
) -> dict:
    server = _get_server(
        server_id,
        db,
    )

    try:
        (
            updater,
            transport,
            method,
            privilege_password,
        ) = _open_update_session(
            server,
            db,
        )

        try:
            result = updater.cleanup(
                transport,
                method,
                privilege_password,
            )

            remaining_updates = updater.list_updates(
                transport
            )

            reboot_status = updater.get_reboot_status(
                transport
            )

        finally:
            transport.close()

        server.reboot_required = (
            reboot_status["reboot_required"]
        )

        db.commit()
        db.refresh(server)

        create_history_entry(
            db=db,
            server=server,
            action=ACTION_CLEANUP,
            status=STATUS_SUCCESS,
            package_count=0,
            reboot_required=server.reboot_required,
            message="Cleanup completed",
        )

        return {
            "server_id": server.id,
            "server": server.name,
            "system_hostname": server.system_hostname,
            "cleanup": result,
            "remaining_updates": len(remaining_updates),
            "reboot_required": server.reboot_required,
        }

    except (
        AuthenticationError,
        PrivilegeUnavailableError,
        PrivilegeError,
        DiscoveryError,
        UpdaterError,
    ) as exc:
        _raise_update_error(
            db,
            server,
            ACTION_CLEANUP,
            exc,
        )
