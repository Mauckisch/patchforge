import re
import shlex

import paramiko


class PacmanError(Exception):
    pass


PACKAGE_NAME_PATTERN = re.compile(
    r"^[A-Za-z0-9@][A-Za-z0-9@+_.:-]*$"
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

    raise PacmanError(
        "Unsupported privilege method "
        f"for pacman: {privilege_method}"
    )


def refresh_package_index(
    transport: paramiko.Transport,
    privilege_method: str,
    privilege_password: str | None,
) -> None:
    # checkupdates uses a temporary pacman database and does not
    # alter the system package database. Exit code 2 means that
    # no updates are currently available.
    status, stdout, stderr = _execute(
        transport,
        "LC_ALL=C checkupdates",
        timeout=600,
    )

    if status not in (0, 2):
        raise PacmanError(
            stderr
            or stdout
            or "Unable to refresh pacman update information"
        )


def list_updates(
    transport: paramiko.Transport,
) -> list[dict]:
    status, stdout, stderr = _execute(
        transport,
        "LC_ALL=C checkupdates",
        timeout=600,
    )

    if status == 2:
        return []

    if status != 0:
        raise PacmanError(
            stderr
            or stdout
            or "Unable to retrieve available pacman updates"
        )

    updates: list[dict] = []

    for raw_line in stdout.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        # checkupdates output:
        # package old_version -> new_version
        match = re.match(
            r"^(\S+)\s+(\S+)\s+->\s+(\S+)$",
            line,
        )

        if match is None:
            raise PacmanError(
                "Unable to parse checkupdates output: "
                f"{line}"
            )

        name, installed_version, available_version = (
            match.groups()
        )

        updates.append(
            {
                "name": name,
                "installed_version": installed_version,
                "available_version": available_version,
                "architecture": "",
                "repository": "pacman",
            }
        )

    return updates


def validate_requested_packages(
    requested_packages: list[str],
    available_updates: list[dict],
) -> list[str]:
    available_names = [
        update["name"]
        for update in available_updates
    ]

    validated: list[str] = []

    for package in requested_packages:
        if not PACKAGE_NAME_PATTERN.fullmatch(
            package
        ):
            raise PacmanError(
                f"Invalid package name: {package}"
            )

        if package not in available_names:
            raise PacmanError(
                "Package is not an installable "
                f"update: {package}"
            )

        if package not in validated:
            validated.append(package)

    if set(validated) != set(available_names):
        raise PacmanError(
            "Selective package updates are not supported "
            "on pacman-based systems. Arch Linux requires "
            "a complete system upgrade."
        )

    return validated


def install_updates(
    transport: paramiko.Transport,
    packages: list[str],
    privilege_method: str,
    privilege_password: str | None,
) -> None:
    if not packages:
        raise PacmanError(
            "No packages selected for installation"
        )

    for package in packages:
        if not PACKAGE_NAME_PATTERN.fullmatch(
            package
        ):
            raise PacmanError(
                f"Invalid package name: {package}"
            )

    # Package names are intentionally not passed to pacman here.
    # Arch Linux only supports complete system upgrades.
    command, stdin_data = _privileged_command(
        "pacman -Syu --noconfirm",
        privilege_method,
        privilege_password,
    )

    status, stdout, stderr = _execute(
        transport,
        command,
        stdin_data=stdin_data,
        timeout=3600,
    )

    if status != 0:
        raise PacmanError(
            stderr
            or stdout
            or "pacman system upgrade failed"
        )


def cleanup_available(
    transport: paramiko.Transport,
) -> bool:
    status, stdout, stderr = _execute(
        transport,
        "LC_ALL=C pacman -Qtdq",
        timeout=120,
    )

    if status == 1 and not stdout:
        return False

    if status != 0:
        raise PacmanError(
            stderr
            or stdout
            or (
                "Unable to determine "
                "pacman cleanup availability"
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
    status, stdout, stderr = _execute(
        transport,
        "LC_ALL=C pacman -Qtdq",
        timeout=120,
    )

    if status == 1 and not stdout:
        return {
            "package_cache_cleaned": False,
            "autoremove_completed": True,
        }

    if status != 0:
        raise PacmanError(
            stderr
            or stdout
            or "Unable to determine pacman orphan packages"
        )

    packages = [
        line.strip()
        for line in stdout.splitlines()
        if line.strip()
    ]

    if not packages:
        return {
            "package_cache_cleaned": False,
            "autoremove_completed": True,
        }

    for package in packages:
        if not PACKAGE_NAME_PATTERN.fullmatch(
            package
        ):
            raise PacmanError(
                f"Invalid orphan package name: {package}"
            )

    package_arguments = " ".join(
        shlex.quote(package)
        for package in packages
    )

    command, stdin_data = _privileged_command(
        (
            "pacman -Rns --noconfirm "
            f"{package_arguments}"
        ),
        privilege_method,
        privilege_password,
    )

    status, stdout, stderr = _execute(
        transport,
        command,
        stdin_data=stdin_data,
        timeout=1800,
    )

    if status != 0:
        raise PacmanError(
            stderr
            or stdout
            or "pacman orphan cleanup failed"
        )

    return {
        "package_cache_cleaned": False,
        "autoremove_completed": True,
    }


def get_reboot_status(
    transport: paramiko.Transport,
) -> dict:
    status, running_kernel, stderr = _execute(
        transport,
        "uname -r",
        timeout=10,
    )

    if status != 0:
        raise PacmanError(
            stderr
            or "Unable to determine running kernel"
        )

    kernel_path = (
        f"/usr/lib/modules/{running_kernel}/vmlinuz"
    )

    status, owner_package, owner_error = _execute(
        transport,
        (
            "LC_ALL=C pacman -Qoq "
            f"{shlex.quote(kernel_path)}"
        ),
        timeout=30,
    )

    reboot_required = False
    reasons: list[dict] = []

    if status != 0 or not owner_package:
        # After a kernel package upgrade, the module directory for
        # the still-running old kernel may already have disappeared.
        reboot_required = True

        reasons.append(
            {
                "type": "kernel_package_changed",
                "message": (
                    "The running kernel is no longer owned by "
                    "an installed pacman package. A newer kernel "
                    "may have been installed."
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
            reboot_required,

        "reasons":
            reasons,
    }
