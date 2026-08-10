import paramiko

from app.services import dnf
from app.updaters.base import (
    BaseUpdater,
    UpdaterError,
)


class DnfUpdater(BaseUpdater):
    name = "dnf"

    def refresh_package_index(
        self,
        transport: paramiko.Transport,
        privilege_method: str,
        privilege_password: str | None,
    ) -> None:
        try:
            dnf.refresh_package_index(
                transport=transport,
                privilege_method=privilege_method,
                privilege_password=privilege_password,
            )

        except dnf.DnfError as exc:
            raise UpdaterError(
                str(exc)
            ) from exc

    def list_updates(
        self,
        transport: paramiko.Transport,
    ) -> list[dict]:
        try:
            return dnf.list_updates(
                transport
            )

        except dnf.DnfError as exc:
            raise UpdaterError(
                str(exc)
            ) from exc

    def validate_requested_packages(
        self,
        requested_packages: list[str],
        available_updates: list[dict],
    ) -> list[str]:
        try:
            return (
                dnf.validate_requested_packages(
                    requested_packages,
                    available_updates,
                )
            )

        except dnf.DnfError as exc:
            raise UpdaterError(
                str(exc)
            ) from exc

    def install_updates(
        self,
        transport: paramiko.Transport,
        packages: list[str],
        privilege_method: str,
        privilege_password: str | None,
    ) -> None:
        try:
            dnf.install_updates(
                transport=transport,
                packages=packages,
                privilege_method=privilege_method,
                privilege_password=privilege_password,
            )

        except dnf.DnfError as exc:
            raise UpdaterError(
                str(exc)
            ) from exc

    def cleanup_available(
        self,
        transport: paramiko.Transport,
    ) -> bool:
        try:
            return dnf.cleanup_available(
                transport
            )

        except dnf.DnfError as exc:
            raise UpdaterError(
                str(exc)
            ) from exc

    def cleanup(
        self,
        transport: paramiko.Transport,
        privilege_method: str,
        privilege_password: str | None,
    ) -> dict:
        try:
            return dnf.cleanup(
                transport=transport,
                privilege_method=privilege_method,
                privilege_password=privilege_password,
            )

        except dnf.DnfError as exc:
            raise UpdaterError(
                str(exc)
            ) from exc

    def get_reboot_status(
        self,
        transport: paramiko.Transport,
    ) -> dict:
        try:
            return dnf.get_reboot_status(
                transport
            )

        except dnf.DnfError as exc:
            raise UpdaterError(
                str(exc)
            ) from exc
