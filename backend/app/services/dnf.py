import re

import paramiko


class DnfError(Exception):
    pass


PACKAGE_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9+_.:-]*$"
)


def _decode(value: str | bytes) -> str:
    if isinstance(value, bytes):
        return value.decode(
            "utf-8",
            errors="replace",
        )

    return value


def _execute(
    transport: paramiko.Transport,
    command: str,
    stdin_data: str | None = None,
    timeout: int = 120,
) -> tuple[int, str, str]:
    channel = transport.open_session(
        timeout=10
    )

    try:
        channel.settimeout(timeout)
        channel.exec_command(command)

        if stdin_data is not None:
            channel.sendall(
                stdin_data.encode("utf-8")
            )
            channel.shutdown_write()

        stdout_raw = (
            channel.makefile("r", -1).read()
        )

        stderr_raw = (
            channel.makefile_stderr(
                "r",
                -1,
            ).read()
        )

        exit_status = (
            channel.recv_exit_status()
        )

        return (
            exit_status,
            _decode(stdout_raw).strip(),
            _decode(stderr_raw).strip(),
        )

    finally:
        channel.close()


def _privileged_command(
    command: str,
    privilege_method: str,
    privilege_password: str | None,
) -> tuple[str, str | None]:
    if privilege_method == "root":
        return (
            f"LC_ALL=C {command}",
            None,
        )

    if privilege_method == "sudo":
        if privilege_password is None:
            return (
                f"sudo -n env LC_ALL=C {command}",
                None,
            )

        return (
            f"sudo -S -p '' env LC_ALL=C {command}",
            f"{privilege_password}\n",
        )

    raise DnfError(
        "Unsupported privilege method "
        f"for DNF: {privilege_method}"
    )


def refresh_package_index(
    transport: paramiko.Transport,
    privilege_method: str,
    privilege_password: str | None,
) -> None:
    command, stdin_data = (
        _privileged_command(
            "dnf -q makecache",
            privilege_method,
            privilege_password,
        )
    )

    status, stdout, stderr = _execute(
        transport,
        command,
        stdin_data=stdin_data,
        timeout=600,
    )

    if status != 0:
        raise DnfError(
            stderr
            or stdout
            or "DNF metadata refresh failed"
        )


def _get_installed_versions(
    transport: paramiko.Transport,
) -> dict[tuple[str, str], str]:
    status, stdout, stderr = _execute(
        transport,
        (
            "LC_ALL=C "
            "dnf -q repoquery "
            "--installed "
            "--qf "
            "'%{name}|%{arch}|%{evr}'"
        ),
        timeout=120,
    )

    if status != 0:
        raise DnfError(
            stderr
            or stdout
            or (
                "Unable to retrieve "
                "installed DNF packages"
            )
        )

    installed: dict[
        tuple[str, str],
        str
    ] = {}

    for raw_line in stdout.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        parts = line.split("|")

        if len(parts) != 3:
            continue

        name, arch, version = parts

        if not name or not arch or not version:
            continue

        installed[(name, arch)] = version

    return installed


def list_updates(
    transport: paramiko.Transport,
) -> list[dict]:
    status, stdout, stderr = _execute(
        transport,
        (
            "LC_ALL=C "
            "dnf -q repoquery "
            "--upgrades "
            "--qf "
            "'%{name}|%{arch}|%{evr}|%{repoid}'"
        ),
        timeout=120,
    )

    if status != 0:
        raise DnfError(
            stderr
            or stdout
            or (
                "Unable to retrieve "
                "available DNF updates"
            )
        )

    installed_versions = (
        _get_installed_versions(
            transport
        )
    )

    updates: list[dict] = []

    seen: set[
        tuple[str, str]
    ] = set()

    for raw_line in stdout.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        parts = line.split("|")

        if len(parts) != 4:
            continue

        (
            name,
            arch,
            available_version,
            repository,
        ) = parts

        key = (
            name,
            arch,
        )

        if key in seen:
            continue

        installed_version = (
            installed_versions.get(key)
        )

        if installed_version is None:
            continue

        updates.append(
            {
                "name": name,
                "installed_version":
                    installed_version,
                "available_version":
                    available_version,
                "architecture": arch,
                "repository": repository,
            }
        )

        seen.add(key)

    return updates


def validate_requested_packages(
    requested_packages: list[str],
    available_updates: list[dict],
) -> list[str]:
    available_names = {
        update["name"]
        for update in available_updates
    }

    validated: list[str] = []

    for package in requested_packages:
        if not PACKAGE_NAME_PATTERN.fullmatch(
            package
        ):
            raise DnfError(
                f"Invalid package name: {package}"
            )

        if package not in available_names:
            raise DnfError(
                "Package is not an installable "
                f"update: {package}"
            )

        if package not in validated:
            validated.append(package)

    return validated


def install_updates(
    transport: paramiko.Transport,
    packages: list[str],
    privilege_method: str,
    privilege_password: str | None,
) -> None:
    if not packages:
        raise DnfError(
            "No packages selected "
            "for installation"
        )

    package_arguments = " ".join(
        packages
    )

    command, stdin_data = (
        _privileged_command(
            (
                "dnf -y upgrade "
                f"{package_arguments}"
            ),
            privilege_method,
            privilege_password,
        )
    )

    status, stdout, stderr = _execute(
        transport,
        command,
        stdin_data=stdin_data,
        timeout=1800,
    )

    if status != 0:
        raise DnfError(
            stderr
            or stdout
            or (
                "DNF update "
                "installation failed"
            )
        )


def cleanup_available(
    transport: paramiko.Transport,
) -> bool:
    status, stdout, stderr = _execute(
        transport,
        (
            "LC_ALL=C "
            "dnf -q repoquery "
            "--unneeded "
            "--qf "
            "'%{name}|%{arch}|%{evr}'"
        ),
        timeout=120,
    )

    if status != 0:
        raise DnfError(
            stderr
            or stdout
            or (
                "Unable to determine "
                "DNF cleanup availability"
            )
        )

    return any(
        line.strip()
        for line in stdout.splitlines()
    )


def cleanup(
    transport: paramiko.Transport,
    privilege_method: str,
    privilege_password: str | None,
) -> dict:
    clean_command, clean_stdin = (
        _privileged_command(
            "dnf clean packages",
            privilege_method,
            privilege_password,
        )
    )

    status, stdout, stderr = _execute(
        transport,
        clean_command,
        stdin_data=clean_stdin,
        timeout=600,
    )

    if status != 0:
        raise DnfError(
            stderr
            or stdout
            or "DNF package cache cleanup failed"
        )

    autoremove_command, autoremove_stdin = (
        _privileged_command(
            "dnf -y autoremove",
            privilege_method,
            privilege_password,
        )
    )

    status, stdout, stderr = _execute(
        transport,
        autoremove_command,
        stdin_data=autoremove_stdin,
        timeout=1800,
    )

    if status != 0:
        raise DnfError(
            stderr
            or stdout
            or "DNF autoremove failed"
        )

    return {
        "package_cache_cleaned": True,
        "autoremove_completed": True,
    }


def get_reboot_status(
    transport: paramiko.Transport,
) -> dict:
    status, stdout, stderr = _execute(
        transport,
        (
            "LC_ALL=C "
            "dnf needs-restarting -r"
        ),
        timeout=120,
    )

    if status not in (
        0,
        1,
    ):
        raise DnfError(
            stderr
            or stdout
            or (
                "Unable to determine "
                "DNF reboot status"
            )
        )

    reboot_required = (
        status == 1
    )

    kernel_status, running_kernel, kernel_error = (
        _execute(
            transport,
            "uname -r",
            timeout=10,
        )
    )

    if kernel_status != 0:
        raise DnfError(
            kernel_error
            or (
                "Unable to determine "
                "running kernel"
            )
        )

    reasons: list[dict] = []

    if reboot_required:
        reasons.append(
            {
                "type": "dnf_needs_restarting",
                "message": (
                    "DNF reports that a system "
                    "reboot is required."
                ),
            }
        )

    return {
        "reboot_required":
            reboot_required,

        "reboot_flag_present":
            False,

        "running_kernel":
            running_kernel,

        "newest_installed_kernel":
            None,

        "newer_kernel_installed":
            False,

        "reasons":
            reasons,
    }
