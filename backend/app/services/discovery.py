import base64
import hashlib
import socket
from dataclasses import dataclass

import paramiko


class DiscoveryError(Exception):
    pass


class AuthenticationError(DiscoveryError):
    pass


class HostKeyMismatchError(DiscoveryError):
    pass


class UnsupportedDistributionError(DiscoveryError):
    pass


@dataclass
class DiscoveryResult:
    hostname: str
    distribution: str
    distribution_version: str
    package_manager: str
    architecture: str
    kernel_version: str
    host_key_fingerprint: str


PACKAGE_MANAGER_PATHS = {
    "apt": ["/usr/bin/apt-get"],
    "dnf": ["/usr/bin/dnf", "/bin/dnf"],
    "apk": ["/sbin/apk"],
    "zypper": ["/usr/bin/zypper"],
    "pacman": ["/usr/bin/pacman"],
}


DISTRIBUTION_PACKAGE_MANAGERS = {
    "debian": "apt",
    "ubuntu": "apt",
    "linuxmint": "apt",

    "ol": "dnf",
    "rhel": "dnf",
    "rocky": "dnf",
    "almalinux": "dnf",
    "fedora": "dnf",
    "centos": "dnf",

    "alpine": "apk",

    "opensuse-leap": "zypper",
    "opensuse-tumbleweed": "zypper",
    "sles": "zypper",

    "arch": "pacman",
}


def _parse_os_release(content: str) -> dict[str, str]:
    values: dict[str, str] = {}

    for line in content.splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ("'", '"')
        ):
            value = value[1:-1]

        values[key.strip()] = value

    return values


def _fingerprint_sha256(key: paramiko.PKey) -> str:
    digest = hashlib.sha256(key.asbytes()).digest()

    encoded = base64.b64encode(
        digest
    ).decode("ascii").rstrip("=")

    return f"SHA256:{encoded}"


def _execute_fixed_command(
    transport: paramiko.Transport,
    command: str,
) -> str:
    channel = transport.open_session(timeout=10)

    try:
        channel.exec_command(command)

        stdout = channel.makefile("r", -1).read()
        stderr = channel.makefile_stderr("r", -1).read()

        exit_status = channel.recv_exit_status()

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")

        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        if exit_status != 0:
            raise DiscoveryError(
                f"Discovery command failed: {stderr.strip()}"
            )

        return stdout.strip()

    finally:
        channel.close()


def _path_exists(
    sftp: paramiko.SFTPClient,
    path: str,
) -> bool:
    try:
        sftp.stat(path)
        return True
    except OSError:
        return False


def _detect_package_manager(
    sftp: paramiko.SFTPClient,
    distribution_id: str,
) -> str:
    expected = DISTRIBUTION_PACKAGE_MANAGERS.get(
        distribution_id
    )

    if expected is None:
        raise UnsupportedDistributionError(
            f"Unsupported Linux distribution: {distribution_id}"
        )

    if not any(
        _path_exists(sftp, path)
        for path in PACKAGE_MANAGER_PATHS[expected]
    ):
        raise UnsupportedDistributionError(
            f"Expected package manager '{expected}' was not found"
        )

    return expected


def discover_server(
    host: str,
    port: int,
    username: str,
    password: str,
    expected_host_key: str | None = None,
) -> DiscoveryResult:
    sock = None
    transport = None

    try:
        sock = socket.create_connection(
            (host, port),
            timeout=10,
        )

        transport = paramiko.Transport(sock)
        transport.start_client(timeout=10)

        remote_key = transport.get_remote_server_key()
        fingerprint = _fingerprint_sha256(remote_key)

        if (
            expected_host_key is not None
            and expected_host_key != fingerprint
        ):
            raise HostKeyMismatchError(
                "SSH host key has changed"
            )

        try:
            transport.auth_password(
                username=username,
                password=password,
            )

        except paramiko.AuthenticationException as exc:
            raise AuthenticationError(
                "SSH authentication failed"
            ) from exc

        if not transport.is_authenticated():
            raise AuthenticationError(
                "SSH authentication failed"
            )

        sftp = paramiko.SFTPClient.from_transport(transport)

        try:
            with sftp.open("/etc/os-release", "r") as file:
                content = file.read()

                if isinstance(content, bytes):
                    content = content.decode(
                        "utf-8",
                        errors="replace",
                    )

            os_release = _parse_os_release(content)

            distribution_id = (
                os_release.get("ID", "")
                .strip()
                .lower()
            )

            if not distribution_id:
                raise UnsupportedDistributionError(
                    "Distribution ID could not be detected"
                )

            distribution_name = os_release.get(
                "PRETTY_NAME",
                distribution_id,
            )

            distribution_version = os_release.get(
                "VERSION_ID",
                "",
            )

            package_manager = _detect_package_manager(
                sftp,
                distribution_id,
            )

            hostname = _execute_fixed_command(
                transport,
                "hostname",
            )

            architecture = _execute_fixed_command(
                transport,
                "uname -m",
            )

            kernel_version = _execute_fixed_command(
                transport,
                "uname -r",
            )

        finally:
            sftp.close()

        return DiscoveryResult(
            hostname=hostname,
            distribution=distribution_name,
            distribution_version=distribution_version,
            package_manager=package_manager,
            architecture=architecture,
            kernel_version=kernel_version,
            host_key_fingerprint=fingerprint,
        )

    except (
        HostKeyMismatchError,
        AuthenticationError,
        UnsupportedDistributionError,
    ):
        raise

    except (
        socket.timeout,
        TimeoutError,
        ConnectionError,
        OSError,
        paramiko.SSHException,
    ) as exc:
        raise DiscoveryError(
            f"SSH connection failed: {exc}"
        ) from exc

    finally:
        if transport is not None:
            transport.close()

        if sock is not None:
            sock.close()
