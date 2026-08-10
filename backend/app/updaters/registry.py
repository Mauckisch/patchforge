from app.updaters.apt import AptUpdater
from app.updaters.dnf import DnfUpdater
from app.updaters.base import BaseUpdater, UpdaterError


UPDATERS: dict[str, BaseUpdater] = {
    "apt": AptUpdater(),
    "dnf": DnfUpdater(),
}


def get_updater(
    package_manager: str | None,
) -> BaseUpdater:
    if not package_manager:
        raise UpdaterError(
            "No package manager detected"
        )

    updater = UPDATERS.get(
        package_manager
    )

    if updater is None:
        raise UpdaterError(
            f"Unsupported package manager: {package_manager}"
        )

    return updater
