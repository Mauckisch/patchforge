import subprocess

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.credentials import decrypt_secret
from app.core.dependencies import get_db
from app.models.credential import ServerCredential
from app.models.server import Server
from app.services.discovery import (
    AuthenticationError,
    DiscoveryError,
)
from app.services.notifications import (
    EVENT_SERVER_OFFLINE,
    EVENT_SERVER_ONLINE,
    EVENT_SSH_ERROR,
    send_notification_event,
)
from app.services.privilege import _open_transport
from app.services.server_status import (
    mark_error,
    mark_online,
    mark_unreachable,
)


router = APIRouter(
    prefix="/api/servers",
    tags=["status"],
)


def _ping_host(
    host: str,
) -> bool:
    try:
        result = subprocess.run(
            [
                "ping",
                "-c",
                "1",
                "-W",
                "2",
                host,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
        )

        return result.returncode == 0

    except (
        FileNotFoundError,
        subprocess.TimeoutExpired,
        OSError,
    ):
        return False


def _notify_status_transition(
    db: Session,
    server: Server,
    previous_status: str,
) -> None:
    current_status = server.connection_status

    if current_status == previous_status:
        return

    if current_status == "UNREACHABLE":
        send_notification_event(
            db=db,
            event_key=EVENT_SERVER_OFFLINE,
            title=f"{server.name} is offline",
            message=(
                f"Server: {server.name}\n"
                f"Host: {server.host}\n"
                f"Previous status: {previous_status}\n"
                f"Current status: {current_status}\n"
                f"Reason: {server.last_error or 'Host unreachable'}"
            ),
        )

        return

    if (
        current_status == "ONLINE"
        and previous_status
        in {
            "UNREACHABLE",
            "ERROR",
            "AUTH_FAILED",
        }
    ):
        send_notification_event(
            db=db,
            event_key=EVENT_SERVER_ONLINE,
            title=f"{server.name} is online again",
            message=(
                f"Server: {server.name}\n"
                f"Host: {server.host}\n"
                f"Previous status: {previous_status}\n"
                f"Current status: {current_status}"
            ),
        )

        return

    if current_status == "ERROR":
        send_notification_event(
            db=db,
            event_key=EVENT_SSH_ERROR,
            title=f"SSH error on {server.name}",
            message=(
                f"Server: {server.name}\n"
                f"Host: {server.host}\n"
                f"Previous status: {previous_status}\n"
                f"Current status: {current_status}\n"
                f"Reason: {server.last_error or 'SSH connection failed'}"
            ),
        )


def _check_server(
    server: Server,
    db: Session,
) -> dict:
    previous_status = (
        server.connection_status
    )

    credential = db.scalar(
        select(ServerCredential).where(
            ServerCredential.server_id == server.id
        )
    )

    if credential is None:
        mark_error(
            server,
            "No credentials configured",
        )

        db.commit()

        return {
            "server_id": server.id,
            "status": server.connection_status,
            "last_seen_at": server.last_seen_at,
            "last_check_at": server.last_check_at,
            "last_error": server.last_error,
        }

    ssh_password = decrypt_secret(
        credential.ssh_password_nonce,
        credential.ssh_password_ciphertext,
    )

    ping_reachable = _ping_host(
        server.host
    )

    transport = None

    try:
        transport = _open_transport(
            host=server.host,
            port=server.ssh_port,
            username=server.username,
            password=ssh_password,
        )

        # SSH is the authoritative PatchForge
        # connectivity check. A host remains ONLINE
        # even when ICMP/ping is blocked.
        mark_online(
            server
        )

    except AuthenticationError:
        if ping_reachable:
            mark_error(
                server,
                "Host reachable, but SSH authentication failed",
            )
        else:
            mark_unreachable(
                server,
                "Ping failed and SSH authentication failed",
            )

    except DiscoveryError as exc:
        if ping_reachable:
            mark_error(
                server,
                str(exc),
            )
        else:
            mark_unreachable(
                server,
                str(exc),
            )

    except Exception as exc:
        if ping_reachable:
            mark_error(
                server,
                str(exc),
            )
        else:
            mark_unreachable(
                server,
                str(exc),
            )

    finally:
        if transport is not None:
            transport.close()

    db.commit()
    db.refresh(server)

    _notify_status_transition(
        db,
        server,
        previous_status,
    )

    return {
        "server_id": server.id,
        "status": server.connection_status,
        "last_seen_at": server.last_seen_at,
        "last_check_at": server.last_check_at,
        "last_error": server.last_error,
    }


@router.post("/{server_id}/status-check")
def check_server_status(
    server_id: int,
    db: Session = Depends(get_db),
) -> dict:
    server = db.get(
        Server,
        server_id,
    )

    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )

    return _check_server(
        server,
        db,
    )


@router.post("/status-check")
def check_all_server_status(
    db: Session = Depends(get_db),
) -> dict:
    servers = list(
        db.scalars(
            select(Server)
            .order_by(Server.name)
        ).all()
    )

    results = [
        _check_server(
            server,
            db,
        )
        for server in servers
    ]

    return {
        "checked": len(results),
        "results": results,
    }
