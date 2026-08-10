from datetime import datetime

from app.models.server import Server


STATUS_UNKNOWN = "UNKNOWN"
STATUS_ONLINE = "ONLINE"
STATUS_AUTH_FAILED = "AUTH_FAILED"
STATUS_UNREACHABLE = "UNREACHABLE"
STATUS_ERROR = "ERROR"


def mark_online(
    server: Server,
) -> None:
    now = datetime.utcnow()

    server.connection_status = STATUS_ONLINE
    server.last_seen_at = now
    server.last_check_at = now
    server.last_error = None


def mark_auth_failed(
    server: Server,
    message: str,
) -> None:
    server.connection_status = STATUS_AUTH_FAILED
    server.last_check_at = datetime.utcnow()
    server.last_error = message


def mark_unreachable(
    server: Server,
    message: str,
) -> None:
    server.connection_status = STATUS_UNREACHABLE
    server.last_check_at = datetime.utcnow()
    server.last_error = message


def mark_error(
    server: Server,
    message: str,
) -> None:
    server.connection_status = STATUS_ERROR
    server.last_check_at = datetime.utcnow()
    server.last_error = message
