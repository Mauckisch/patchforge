import re
import time

import paramiko


class AptError(Exception):
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


def _execute_streaming(
    transport: paramiko.Transport,
    command: str,
    stdin_data: str | None = None,
    timeout: int = 120,
    line_callback=None,
) -> tuple[int, str, str]:
    channel = transport.open_session(
        timeout=10
    )

    stdout_parts: list[str] = []
    stderr_parts: list[str] = []

    stdout_buffer = ""
    stderr_buffer = ""

    started_at = time.monotonic()

    try:
        channel.exec_command(command)

        if stdin_data is not None:
            channel.sendall(
                stdin_data.encode("utf-8")
            )
            channel.shutdown_write()

        while True:
            if (
                time.monotonic()
                - started_at
                > timeout
            ):
                raise AptError(
                    "APT command timed out"
                )

            received_data = False

            while channel.recv_ready():
                received_data = True

                chunk = _decode(
                    channel.recv(32768)
                )

                stdout_parts.append(chunk)
                stdout_buffer += chunk

                while "\n" in stdout_buffer:
                    line, stdout_buffer = (
                        stdout_buffer.split(
                            "\n",
                            1,
                        )
                    )

                    if line_callback is not None:
                        line_callback(
                            line.rstrip("\r")
                        )

            while channel.recv_stderr_ready():
                received_data = True

                chunk = _decode(
                    channel.recv_stderr(32768)
                )

                stderr_parts.append(chunk)
                stderr_buffer += chunk

                while "\n" in stderr_buffer:
                    line, stderr_buffer = (
                        stderr_buffer.split(
                            "\n",
                            1,
                        )
                    )

                    if line_callback is not None:
                        line_callback(
                            line.rstrip("\r")
                        )

            if channel.exit_status_ready():
                if (
                    not channel.recv_ready()
                    and not channel.recv_stderr_ready()
                ):
                    break

            if not received_data:
                time.sleep(0.05)

        if stdout_buffer:
            if line_callback is not None:
                line_callback(
                    stdout_buffer.rstrip("\r")
                )

        if stderr_buffer:
            if line_callback is not None:
                line_callback(
                    stderr_buffer.rstrip("\r")
                )

        exit_status = (
            channel.recv_exit_status()
        )

        return (
            exit_status,
            "".join(stdout_parts).strip(),
            "".join(stderr_parts).strip(),
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

    raise AptError(
        "Unsupported privilege method "
        f"for APT: {privilege_method}"
    )


def refresh_package_index(
    transport: paramiko.Transport,
    privilege_method: str,
    privilege_password: str | None,
) -> None:
    command, stdin_data = (
        _privileged_command(
            "apt-get update",
            privilege_method,
            privilege_password,
        )
    )

    status, stdout, stderr = _execute(
        transport,
        command,
        stdin_data=stdin_data,
        timeout=300,
    )

    if status != 0:
        raise AptError(
            stderr
            or stdout
            or "apt-get update failed"
        )


def _list_upgradable_packages(
    transport: paramiko.Transport,
) -> tuple[list[dict], str]:
    status, stdout, stderr = _execute(
        transport,
        (
            "LC_ALL=C "
            "apt list --upgradable "
            "2>/dev/null"
        ),
        timeout=60,
    )

    if status != 0:
        raise AptError(
            stderr
            or (
                "Unable to retrieve "
                "available APT updates"
            )
        )

    updates: list[dict] = []

    pattern = re.compile(
        r"^(?P<name>[^/]+)/\S+\s+"
        r"(?P<available>\S+)\s+"
        r"\S+\s+"
        r"\[upgradable from: "
        r"(?P<installed>[^\]]+)\]$"
    )

    for line in stdout.splitlines():
        line = line.strip()

        if (
            not line
            or line.startswith("Listing")
        ):
            continue

        match = pattern.match(line)

        if match is None:
            continue

        updates.append(
            {
                "name":
                    match.group("name"),

                "installed_version":
                    match.group(
                        "installed"
                    ),

                "available_version":
                    match.group(
                        "available"
                    ),
            }
        )

    return updates, stdout


def _get_kept_back_packages(
    transport: paramiko.Transport,
) -> set[str]:
    # Use full-upgrade for classification.
    #
    # A normal "apt-get upgrade" intentionally keeps packages back
    # whenever their upgrade requires installing additional packages
    # or changing dependencies. Kernel meta packages are a common
    # example and must not therefore be classified as HELD.
    #
    # Packages still kept back during a full-upgrade simulation are
    # treated as exceptional/held updates by PatchForge.
    status, stdout, stderr = _execute(
        transport,
        (
            "LC_ALL=C "
            "apt-get -s full-upgrade "
            "-o Debug::NoLocking=1"
        ),
        timeout=120,
    )

    if status != 0:
        raise AptError(
            stderr
            or stdout
            or (
                "Unable to determine "
                "kept-back APT packages"
            )
        )

    kept_back: set[str] = set()

    lines = stdout.splitlines()

    collecting = False

    for raw_line in lines:
        line = raw_line.strip()

        if line == (
            "The following packages "
            "have been kept back:"
        ):
            collecting = True
            continue

        if not collecting:
            continue

        if not line:
            continue

        if (
            line.startswith("The following ")
            or re.match(
                r"^\d+\s+upgraded,",
                line,
            )
        ):
            break

        for package in line.split():
            package = package.strip()

            if (
                package
                and PACKAGE_NAME_PATTERN.fullmatch(
                    package
                )
            ):
                kept_back.add(package)

    return kept_back


def list_updates(
    transport: paramiko.Transport,
) -> tuple[
    list[dict],
    list[dict],
    str,
]:
    all_updates, raw_output = (
        _list_upgradable_packages(
            transport
        )
    )

    kept_back_names = (
        _get_kept_back_packages(
            transport
        )
    )

    normal_updates: list[dict] = []
    held_updates: list[dict] = []

    for update in all_updates:
        item = dict(update)

        if (
            update["name"]
            in kept_back_names
        ):
            item["held"] = True

            held_updates.append(
                item
            )

        else:
            item["held"] = False

            normal_updates.append(
                item
            )

    return (
        normal_updates,
        held_updates,
        raw_output,
    )


def validate_requested_packages(
    requested_packages: list[str],
    available_updates: list[dict],
) -> list[str]:
    available_names = {
        update["name"]
        for update in available_updates
        if not update.get(
            "held",
            False,
        )
    }

    validated: list[str] = []

    for package in requested_packages:
        if not PACKAGE_NAME_PATTERN.fullmatch(
            package
        ):
            raise AptError(
                f"Invalid package name: {package}"
            )

        if package not in available_names:
            raise AptError(
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
    progress_callback=None,
) -> None:
    if not packages:
        raise AptError(
            "No packages selected "
            "for installation"
        )

    package_arguments = " ".join(
        packages
    )

    command, stdin_data = (
        _privileged_command(
            (
                "DEBIAN_FRONTEND="
                "noninteractive "
                "apt-get install -y "
                "-o APT::Status-Fd=3 "
                "--only-upgrade "
                f"{package_arguments} "
                "3>&1"
            ),
            privilege_method,
            privilege_password,
        )
    )

    def handle_line(line: str) -> None:
        if progress_callback is None:
            return

        stripped = line.strip()

        if not stripped:
            return

        if not stripped.startswith(
            "pmstatus:"
        ):
            return

        parts = stripped.split(
            ":",
            3,
        )

        if len(parts) != 4:
            return

        _, package_name, percent_raw, description = (
            parts
        )

        try:
            percent = float(
                percent_raw
            )
        except ValueError:
            return

        progress_callback({
            "package": (
                package_name.strip()
                or None
            ),
            "percent": max(
                0.0,
                min(
                    100.0,
                    percent,
                ),
            ),
            "message": description.strip(),
        })

    status, stdout, stderr = _execute_streaming(
        transport,
        command,
        stdin_data=stdin_data,
        timeout=1800,
        line_callback=handle_line,
    )

    if status != 0:
        raise AptError(
            stderr
            or stdout
            or (
                "APT update "
                "installation failed"
            )
        )


def _kernel_sort_key(
    kernel: str,
) -> tuple:
    parts = re.split(
        r"(\d+)",
        kernel,
    )

    key: list[
        tuple[int, int | str]
    ] = []

    for part in parts:
        if not part:
            continue

        if part.isdigit():
            key.append(
                (
                    0,
                    int(part),
                )
            )
        else:
            key.append(
                (
                    1,
                    part.lower(),
                )
            )

    return tuple(key)


def get_kernel_reboot_status(
    transport: paramiko.Transport,
) -> dict:
    flag_status, _, _ = _execute(
        transport,
        (
            "test -f "
            "/var/run/reboot-required"
        ),
        timeout=10,
    )

    reboot_flag = (
        flag_status == 0
    )

    status, running_kernel, stderr = (
        _execute(
            transport,
            "uname -r",
            timeout=10,
        )
    )

    if status != 0:
        raise AptError(
            stderr
            or (
                "Unable to determine "
                "running kernel"
            )
        )

    status, kernel_files, _ = _execute(
        transport,
        (
            "ls -1 "
            "/boot/vmlinuz-* "
            "2>/dev/null"
        ),
        timeout=10,
    )

    installed_kernels: list[str] = []

    if status == 0:
        for line in (
            kernel_files.splitlines()
        ):
            line = line.strip()

            prefix = "/boot/vmlinuz-"

            if line.startswith(prefix):
                kernel = line[
                    len(prefix):
                ]

                if kernel:
                    installed_kernels.append(
                        kernel
                    )

    newest_installed_kernel = None

    newer_kernel_installed = False

    if installed_kernels:
        newest_installed_kernel = max(
            installed_kernels,
            key=_kernel_sort_key,
        )

        newer_kernel_installed = (
            _kernel_sort_key(
                newest_installed_kernel
            )
            > _kernel_sort_key(
                running_kernel
            )
        )

    reboot_required = (
        reboot_flag
        or newer_kernel_installed
    )

    reasons: list[dict] = []

    if newer_kernel_installed:
        reasons.append(
            {
                "type": "kernel",
                "message": (
                    "A newer kernel is "
                    "installed than the "
                    "currently running kernel."
                ),
                "running_kernel":
                    running_kernel,
                "installed_kernel":
                    newest_installed_kernel,
            }
        )

    if reboot_flag:
        reasons.append(
            {
                "type": "reboot_flag",
                "message": (
                    "The operating system "
                    "has created "
                    "/var/run/reboot-required."
                ),
            }
        )

    return {
        "reboot_required":
            reboot_required,

        "reboot_flag_present":
            reboot_flag,

        "running_kernel":
            running_kernel,

        "newest_installed_kernel":
            newest_installed_kernel,

        "newer_kernel_installed":
            newer_kernel_installed,

        "reasons":
            reasons,
    }


def cleanup_available(
    transport: paramiko.Transport,
) -> bool:
    status, stdout, stderr = _execute(
        transport,
        (
            "LC_ALL=C "
            "apt-get -s autoremove "
            "-o Debug::NoLocking=1"
        ),
        timeout=120,
    )

    if status != 0:
        raise AptError(
            stderr
            or stdout
            or (
                "Unable to determine "
                "APT cleanup availability"
            )
        )

    match = re.search(
        r"(\d+) to remove",
        stdout,
    )

    if match is None:
        return False

    return int(match.group(1)) > 0


def cleanup(
    transport: paramiko.Transport,
    privilege_method: str,
    privilege_password: str | None,
) -> dict:
    autoclean_command, autoclean_stdin = (
        _privileged_command(
            "apt-get autoclean -y",
            privilege_method,
            privilege_password,
        )
    )

    status, stdout, stderr = _execute(
        transport,
        autoclean_command,
        stdin_data=autoclean_stdin,
        timeout=600,
    )

    if status != 0:
        raise AptError(
            stderr
            or stdout
            or "APT autoclean failed"
        )

    autoremove_command, autoremove_stdin = (
        _privileged_command(
            "apt-get autoremove -y",
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
        raise AptError(
            stderr
            or stdout
            or "APT autoremove failed"
        )

    return {
        "autoclean_completed": True,
        "autoremove_completed": True,
    }
