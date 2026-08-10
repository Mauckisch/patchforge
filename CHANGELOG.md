# Changelog

All notable changes to **PatchForge for Linux** are documented in this
file.

PatchForge follows semantic versioning (`MAJOR.MINOR.PATCH`).

## [1.2.0]

### Added

- Added live server search to the Servers view.
- Server search matches:
  - server name
  - system hostname
  - IP address / host
  - distribution
  - package manager
- Search is case-insensitive and updates the server list immediately while typing.
- Added a dedicated empty state when no servers match the current search.

## \[1.1.1\]

### Fixed

-   Fixed the application sidebar so it remains anchored to the viewport
    while the main page content is scrolled.
-   The sidebar now consistently occupies the full viewport height.
-   The GitHub repository link remains positioned at the bottom of the
    sidebar instead of scrolling away with long page content.

## \[1.1.0\]

### Added

-   Added persistent update snapshots for managed servers.
    -   Results from the latest update check are stored and restored
        when the update dialog is reopened.
    -   Available updates no longer disappear simply because the update
        dialog was closed.
    -   The time of the latest update check is retained and displayed.
-   Added explicit handling of APT packages that are held back.
    -   Held-back packages are separated from normal available updates.
    -   Held packages do not contribute to the normal update count.
    -   A server is not considered to require normal package updates
        solely because held packages exist.
    -   Held packages are hidden from the normal update list by default.
    -   A dedicated control allows held packages to be displayed when
        required.
    -   Held packages are clearly marked and accompanied by a warning
        explaining the potential risks of installing them.
    -   Held packages can be selected individually for an explicit
        manual installation.
    -   Installation of selected held packages requires a separate
        warning and confirmation.
-   Added protection to ensure held packages are excluded from normal
    bulk update operations.
    -   `Install All` operates only on normal available updates.
    -   Scheduled `INSTALL_ALL` tasks operate only on normal available
        updates.
    -   Held packages are never implicitly included in normal or
        scheduled update installations.
    -   Installation of held packages is restricted to the explicit
        manual held-package workflow.

### Changed

-   Improved APT update detection to distinguish normally upgradeable
    packages from packages held back by APT.
-   Update API responses and saved snapshots now contain normal and held
    update information separately.
-   Dashboard and server update counts represent actionable normal
    updates rather than including held packages.
-   Extended frontend update state and API types to support held-package
    information.
-   Improved the update dialog to preserve and restore the most recently
    checked package state.
-   Improved task create/edit dialogs so long dialogs can be scrolled
    instead of being clipped by the viewport.

### Fixed

-   Fixed update lists becoming empty after closing and reopening the
    server update dialog.
-   Fixed frontend type inconsistencies introduced while adding
    persistent update snapshots.
-   Fixed date handling that could cause the frontend to crash with
    `RangeError: Invalid time value`.
-   Fixed task configuration dialogs being inaccessible at the bottom on
    smaller displays or when their content exceeded the viewport height.

### Safety

-   Held-back packages are intentionally treated as exceptional updates.
-   They are excluded from automatic, scheduled, and normal bulk
    installation paths.
-   This protects systems such as FreePBX where distribution or
    vendor-specific packages may intentionally be held and must not be
    upgraded through a generic system update operation.

## \[1.0.0\]

### Added

-   Initial release of PatchForge for Linux.
-   Web-based management of Linux servers over SSH.
-   Server discovery and storage of detected system information.
-   APT/Debian package update support.
-   Manual package update checks.
-   Installation of selected available updates.
-   Installation of all normal available updates.
-   Package cleanup operations.
-   Reboot-required detection without providing a remote reboot
    function.
-   Kernel-based reboot detection by comparing the running kernel with
    installed kernels.
-   Server connection and online-status tracking.
-   Scheduled task support for update checks, update installation,
    cleanup, and reboot-status checks.
-   Support for assigning scheduled tasks to one or more managed
    servers.
-   Configurable task schedules and time zones.
-   Update and action history.
-   Configurable history retention with a default retention period of 7
    days and an Unlimited option.
-   Secure storage of server credentials.
-   Support for privilege detection and privileged package operations.
-   Dashboard with server, update, reboot, task, and history
    information.
-   Docker-based deployment.
-   Separate production and development Docker Compose configuration.
-   Git-ready project structure with secrets, environment files, and
    database files excluded from version control.
-   GitHub repository link integrated into the web interface.

### Scope

-   Initial package-management support focuses on APT-based Debian
    systems.
-   Additional package managers and distributions are intentionally
    deferred to future releases.
-   PatchForge does not provide remote reboot, shell, terminal,
    arbitrary command execution, or other general-purpose remote
    administration functionality.
