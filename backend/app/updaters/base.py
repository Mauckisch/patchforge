from abc import ABC, abstractmethod

import paramiko


class UpdaterError(Exception):
    pass


class BaseUpdater(ABC):
    name: str

    @abstractmethod
    def refresh_package_index(
        self,
        transport: paramiko.Transport,
        privilege_method: str,
        privilege_password: str | None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_updates(
        self,
        transport: paramiko.Transport,
    ) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def validate_requested_packages(
        self,
        requested_packages: list[str],
        available_updates: list[dict],
    ) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def install_updates(
        self,
        transport: paramiko.Transport,
        packages: list[str],
        privilege_method: str,
        privilege_password: str | None,
        progress_callback=None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def cleanup_available(
        self,
        transport: paramiko.Transport,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    def cleanup(
        self,
        transport: paramiko.Transport,
        privilege_method: str,
        privilege_password: str | None,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_reboot_status(
        self,
        transport: paramiko.Transport,
    ) -> dict:
        raise NotImplementedError
