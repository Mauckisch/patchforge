import paramiko

from app.services import apt
from app.updaters.base import (
    BaseUpdater,
    UpdaterError,
)


class AptUpdater(BaseUpdater):
    name = "apt"

    def refresh_package_index(
        self,
        transport: paramiko.Transport,
        privilege_method: str,
        privilege_password: str | None,
    ) -> None:
        try:
            apt.refresh_package_index(
                transport=transport,
                privilege_method=privilege_method,
                privilege_password=privilege_password,
            )

        except apt.AptError as exc:
            raise UpdaterError(
                str(exc)
            ) from exc

    def list_updates(
        self,
        transport: paramiko.Transport,
    ) -> list[dict]:
        try:
            updates, _, _ = (
                apt.list_updates(
                    transport
                )
            )

            return updates

        except apt.AptError as exc:
            raise UpdaterError(
                str(exc)
            ) from exc

    def list_update_state(
        self,
        transport: paramiko.Transport,
    ) -> dict:
        try:
            (
                updates,
                held_updates,
                raw_output,
            ) = apt.list_updates(
                transport
            )

            return {
                "updates": updates,
                "held_updates":
                    held_updates,
                "raw_output":
                    raw_output,
            }

        except apt.AptError as exc:
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
                apt.validate_requested_packages(
                    requested_packages,
                    available_updates,
                )
            )

        except apt.AptError as exc:
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
            apt.install_updates(
                transport=transport,
                packages=packages,
                privilege_method=privilege_method,
                privilege_password=privilege_password,
            )

        except apt.AptError as exc:
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
            return apt.cleanup(
                transport=transport,
                privilege_method=privilege_method,
                privilege_password=privilege_password,
            )

        except apt.AptError as exc:
            raise UpdaterError(
                str(exc)
            ) from exc

    def get_reboot_status(
        self,
        transport: paramiko.Transport,
    ) -> dict:
        try:
            return (
                apt.get_kernel_reboot_status(
                    transport
                )
            )

        except apt.AptError as exc:
            raise UpdaterError(
                str(exc)
            ) from exc
