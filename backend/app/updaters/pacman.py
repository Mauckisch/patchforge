import paramiko

from app.services import pacman
from app.updaters.base import (
    BaseUpdater,
    UpdaterError,
)


class PacmanUpdater(BaseUpdater):
    name = "pacman"

    def refresh_package_index(
        self,
        transport: paramiko.Transport,
        privilege_method: str,
        privilege_password: str | None,
    ) -> None:
        try:
            pacman.refresh_package_index(
                transport=transport,
                privilege_method=privilege_method,
                privilege_password=privilege_password,
            )
        except pacman.PacmanError as exc:
            raise UpdaterError(str(exc)) from exc

    def list_updates(
        self,
        transport: paramiko.Transport,
    ) -> list[dict]:
        try:
            return pacman.list_updates(transport)
        except pacman.PacmanError as exc:
            raise UpdaterError(str(exc)) from exc

    def validate_requested_packages(
        self,
        requested_packages: list[str],
        available_updates: list[dict],
    ) -> list[str]:
        try:
            return pacman.validate_requested_packages(
                requested_packages,
                available_updates,
            )
        except pacman.PacmanError as exc:
            raise UpdaterError(str(exc)) from exc

    def install_updates(
        self,
        transport: paramiko.Transport,
        packages: list[str],
        privilege_method: str,
        privilege_password: str | None,
        progress_callback=None,
    ) -> None:
        try:
            pacman.install_updates(
                transport=transport,
                packages=packages,
                privilege_method=privilege_method,
                privilege_password=privilege_password,
            )
        except pacman.PacmanError as exc:
            raise UpdaterError(str(exc)) from exc

    def cleanup_available(
        self,
        transport: paramiko.Transport,
    ) -> bool:
        try:
            return pacman.cleanup_available(transport)
        except pacman.PacmanError as exc:
            raise UpdaterError(str(exc)) from exc

    def cleanup(
        self,
        transport: paramiko.Transport,
        privilege_method: str,
        privilege_password: str | None,
    ) -> dict:
        try:
            return pacman.cleanup(
                transport=transport,
                privilege_method=privilege_method,
                privilege_password=privilege_password,
            )
        except pacman.PacmanError as exc:
            raise UpdaterError(str(exc)) from exc

    def get_reboot_status(
        self,
        transport: paramiko.Transport,
    ) -> dict:
        try:
            return pacman.get_reboot_status(transport)
        except pacman.PacmanError as exc:
            raise UpdaterError(str(exc)) from exc
