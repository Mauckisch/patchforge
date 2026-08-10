# Changelog

All notable changes to **PatchForge for Linux** are documented in this
file.

PatchForge follows semantic versioning (`MAJOR.MINOR.PATCH`).

## [1.4.1]

### Fixed

- Fixed manual Run Now execution for disabled scheduled tasks.
- Multi-server tasks now continue processing remaining servers when an individual target is unreachable or fails.
- Scheduled and manually triggered update checks now persist available update, cleanup, and reboot status to the server overview.
- Scheduled and manually triggered Install All and Cleanup tasks now refresh and persist the resulting package state.
- Improved server availability detection by combining SSH connectivity with ICMP ping checks.
- Servers are now reported as Offline when both SSH and ping fail.
- Servers are reported as Error when the host responds to ping but SSH fails.
- Servers remain Online when SSH works even if ICMP ping is blocked.

## [1.4.0]

### Added

- Added DNF package-manager support.
  - Added DNF metadata refresh.
  - Added available-update detection with installed and available versions.
  - Added installation of selected DNF updates.
  - Added installation of all available DNF updates.
  - Added DNF package cleanup support.
  - Added DNF reboot-required detection using `dnf needs-restarting -r`.
- Added persistent cleanup-availability detection for APT and DNF systems.
- Added cleanup status to the server overview.
- Added cleanup status to the update dialog.
- Added package-manager and connection-status filters to the server overview.

### Changed

- Reworked the Servers page from card-based tiles to a compact table/list view.
- Server overview now displays distribution, package manager, connection status, kernel, available updates, reboot status, cleanup status, and actions in one view.
- Cleanup actions are disabled when PatchForge knows that no removable package leftovers are present.
- Cleanup availability is refreshed during update checks and after cleanup operations.
- Existing servers use an Unknown cleanup state until their package state has been checked.
- Updated project documentation for APT and DNF support.

### Fixed

- Cleanup availability now persists across page reloads and reopened update dialogs.
- DNF cleanup detection now uses DNF's unneeded-package query instead of localized human-readable output.

## [1.3.4]

### Added

- Added automatic server connection-status monitoring.
- Server status is checked automatically when PatchForge is loaded and refreshed every 60 seconds.
- Added dedicated Online, Offline, Authentication failed, Error, and Unknown status indicators.

### Changed

- Server cards now display the actual SSH connection status instead of always showing Ready.
- Reboot-required status is displayed separately from the server connection status.
- Offline or otherwise unavailable servers no longer offer package update actions.
- Edit and Delete actions remain available for unavailable servers.

### Fixed

- Fixed powered-off or unreachable servers continuing to appear as Ready.
- Fixed SSH connection failures only becoming visible after manually attempting an update check.
- Fixed Add Server errors being displayed behind the modal instead of inside the Add Server dialog.

## [1.3.3]

### Fixed

- Fixed ARM64 Docker image builds failing during the frontend build
  under QEMU emulation.
- The architecture-independent React/Vite frontend is now built on the
  native Docker build platform instead of being rebuilt under target
  architecture emulation.
- Improved reliability and performance of multi-platform Docker builds
  for `linux/amd64` and `linux/arm64`.

## [1.3.2]

### Added

- Added visible operation status feedback to the update interface.
  - Update checks now display an active operation status.
  - Selected package installations display their current operation.
  - Install All displays an active installation status.
  - Package cleanup displays an active cleanup status.
  - Held-package installations display an active installation status.
- Added a spinner while package-management operations are running.
- Added persistent success feedback after an operation completes.
- Added a dedicated failure state for unsuccessful operations.
- Added automatic GitHub Release creation for version tags.
- GitHub Release notes are automatically extracted from the matching
  version section in `CHANGELOG.md`.

### Changed

- GitHub Actions now has permission to create repository releases in
  addition to publishing Docker images.
- Release tags continue to publish versioned and `latest` Docker images
  while also creating the corresponding GitHub Release.

### Fixed

- Fixed the main application layout being able to expand beyond the
  available viewport width.
- Made the main content grid properly shrink within the available
  horizontal space.
- Fixed dashboard content being cut off on the right side at certain
  viewport sizes.

## [1.3.1]

### Added

- Added a complete visual identity for PatchForge for Linux.
  - Added the official PatchForge logo.
  - Added a standalone PatchForge application icon.
  - Added a dedicated SVG favicon.
  - Added favicon artwork designed to remain clearly visible on dark
    browser and operating-system interfaces.
- Added the PatchForge project logo to the GitHub README.

### Changed

- Replaced the previous text-based `P` sidebar mark with the official
  PatchForge application icon.
- Updated application branding to consistently use the new PatchForge
  visual identity across the web interface, browser favicon, and
  project documentation.

### Fixed

- Fixed APT update classification that could incorrectly report normal
  package updates as held packages.
- Improved the distinction between packages explicitly held by APT and
  packages that cannot be installed by a normal `apt-get upgrade`
  because the upgrade requires dependency changes.
- Packages requiring a full APT upgrade path are no longer
  automatically treated as explicitly held packages solely because
  `apt-get upgrade` reports them as kept back.

### Safety

- Explicitly held packages continue to use PatchForge's protected
  held-package workflow.
- The classification fix does not weaken the existing protection for
  held packages or persistent PatchForge package locks.

## [1.3.0]

### Added

- Added persistent per-server package locks.
  - Individual packages can be explicitly locked from the update
    interface.
  - Locked packages are marked with a lock icon in the update list.
  - Package locks are stored persistently and remain active across
    update checks, application restarts, and new package versions.
  - Locks are maintained independently for each managed server.
  - Locked packages remain visible so administrators can still see that
    an update is available.
  - Package locks can be removed explicitly from the update interface.
- Added package-lock support for both normal available updates and
  packages reported as held back by APT.
- Added backend API endpoints for retrieving, creating, and removing
  persistent package locks.

### Changed

- Normal update selection now automatically excludes locked packages.
- Locked packages cannot be selected for manual package installation
  until their lock is removed.
- `Install All` excludes all packages locked for the target server.
- Scheduled `INSTALL_ALL` tasks exclude all packages locked for the
  target server.
- Held-package installation also respects persistent PatchForge package
  locks.
- Update snapshots now expose the lock state of packages to the
  frontend.
- Package locks are kept separately from update snapshots so refreshing
  or replacing an update snapshot does not remove an administrator's
  package exclusions.

### Safety

- Package locks are enforced by the backend rather than only by the
  frontend.
- A locked package cannot be installed through the normal selected
  update installation API.
- A locked package cannot be installed through `Install All`.
- A locked package cannot be installed by a scheduled `INSTALL_ALL`
  task.
- A locked held-back package cannot be explicitly installed through the
  held-package installation workflow until its PatchForge lock is
  removed.
- PatchForge package locks are independent from APT's own held-package
  state. APT-held packages continue to use the separate held-package
  safety workflow introduced in version 1.1.0.

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
