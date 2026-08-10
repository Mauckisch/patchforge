import socket

import paramiko

from app.services.discovery import (
    AuthenticationError,
    DiscoveryError,
)


class PrivilegeError(Exception):
    pass


class PrivilegeUnavailableError(PrivilegeError):
    def __init__(
        self,
        message: str,
        diagnostics: dict | None = None,
    ):
        super().__init__(message)
        self.diagnostics = diagnostics or {}


def _decode_output(value: str | bytes) -> str:
    if isinstance(value, bytes):
        return value.decode(
            "utf-8",
            errors="replace",
        )

    return value


def _open_transport(
    host: str,
    port: int,
    username: str,
    password: str,
) -> paramiko.Transport:
    try:
        sock = socket.create_connection(
            (host, port),
            timeout=10,
        )

        transport = paramiko.Transport(sock)
        transport.start_client(timeout=10)

        try:
            transport.auth_password(
                username=username,
                password=password,
            )
        except paramiko.AuthenticationException as exc:
            transport.close()

            raise AuthenticationError(
                "SSH authentication failed"
            ) from exc

        if not transport.is_authenticated():
            transport.close()

            raise AuthenticationError(
                "SSH authentication failed"
            )

        return transport

    except AuthenticationError:
        raise

    except Exception as exc:
        raise DiscoveryError(
            f"SSH connection failed: {exc}"
        ) from exc


def _execute(
    transport: paramiko.Transport,
    command: str,
    stdin_data: str | None = None,
) -> tuple[int, str, str]:
    channel = transport.open_session(timeout=10)

    try:
        channel.exec_command(command)

        if stdin_data is not None:
            channel.sendall(
                stdin_data.encode("utf-8")
            )
            channel.shutdown_write()

        stdout_raw = channel.makefile(
            "r",
            -1,
        ).read()

        stderr_raw = channel.makefile_stderr(
            "r",
            -1,
        ).read()

        exit_status = channel.recv_exit_status()

        stdout = _decode_output(
            stdout_raw
        ).strip()

        stderr = _decode_output(
            stderr_raw
        ).strip()

        return (
            exit_status,
            stdout,
            stderr,
        )

    finally:
        channel.close()


def detect_privilege_method(
    host: str,
    port: int,
    username: str,
    ssh_password: str,
    configured_method: str,
    privilege_password: str | None,
) -> dict:
    diagnostics: dict = {}

    transport = _open_transport(
        host=host,
        port=port,
        username=username,
        password=ssh_password,
    )

    try:
        status, stdout, stderr = _execute(
            transport,
            "id -u",
        )

        diagnostics["id"] = {
            "exit_status": status,
            "stdout": stdout,
            "stderr": stderr,
        }

        if status != 0:
            raise PrivilegeUnavailableError(
                "Unable to determine remote user ID",
                diagnostics,
            )

        if stdout == "0":
            return {
                "available": True,
                "method": "root",
                "password_required": False,
                "diagnostics": diagnostics,
            }

        if configured_method == "none":
            return {
                "available": False,
                "method": "none",
                "password_required": False,
                "diagnostics": diagnostics,
            }

        methods_to_try = (
            ["sudo", "su"]
            if configured_method == "auto"
            else [configured_method]
        )

        for method in methods_to_try:
            if method == "sudo":
                result = _test_sudo(
                    transport=transport,
                    ssh_password=ssh_password,
                    privilege_password=privilege_password,
                    diagnostics=diagnostics,
                )

                if result is not None:
                    return result

            elif method == "su":
                result = _test_su(
                    transport=transport,
                    privilege_password=privilege_password,
                    diagnostics=diagnostics,
                )

                if result is not None:
                    return result

        raise PrivilegeUnavailableError(
            "No usable privilege escalation method found",
            diagnostics,
        )

    finally:
        transport.close()


def _test_sudo(
    transport: paramiko.Transport,
    ssh_password: str,
    privilege_password: str | None,
    diagnostics: dict,
) -> dict | None:
    status, stdout, stderr = _execute(
        transport,
        "command -v sudo",
    )

    diagnostics["sudo_present"] = {
        "exit_status": status,
        "stdout": stdout,
        "stderr": stderr,
    }

    if status != 0:
        return None

    status, stdout, stderr = _execute(
        transport,
        "sudo -n id -u",
    )

    diagnostics["sudo_noninteractive"] = {
        "exit_status": status,
        "stdout": stdout,
        "stderr": stderr,
    }

    if status == 0 and stdout == "0":
        return {
            "available": True,
            "method": "sudo",
            "password_required": False,
            "diagnostics": diagnostics,
        }

    password = (
        privilege_password
        if privilege_password is not None
        else ssh_password
    )

    status, stdout, stderr = _execute(
        transport,
        "sudo -S -p '' id -u",
        stdin_data=f"{password}\n",
    )

    diagnostics["sudo_password"] = {
        "exit_status": status,
        "stdout": stdout,
        "stderr": stderr,
        "used_separate_privilege_password": (
            privilege_password is not None
        ),
    }

    if status == 0 and stdout == "0":
        return {
            "available": True,
            "method": "sudo",
            "password_required": True,
            "diagnostics": diagnostics,
        }

    return None


def _test_su(
    transport: paramiko.Transport,
    privilege_password: str | None,
    diagnostics: dict,
) -> dict | None:
    status, stdout, stderr = _execute(
        transport,
        "command -v su",
    )

    diagnostics["su_present"] = {
        "exit_status": status,
        "stdout": stdout,
        "stderr": stderr,
    }

    if status != 0:
        return None

    if privilege_password is None:
        diagnostics["su_password"] = {
            "configured": False,
        }

        return None

    status, stdout, stderr = _execute(
        transport,
        "su -c 'id -u'",
        stdin_data=f"{privilege_password}\n",
    )

    diagnostics["su_password"] = {
        "configured": True,
        "exit_status": status,
        "stdout": stdout,
        "stderr": stderr,
    }

    if status == 0 and stdout == "0":
        return {
            "available": True,
            "method": "su",
            "password_required": True,
            "diagnostics": diagnostics,
        }

    return None
