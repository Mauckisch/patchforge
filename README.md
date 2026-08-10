# PatchForge for Linux

PatchForge for Linux is a focused web application for managing package updates on Linux servers.

Current version: **1.1.0**

## Features

- Manage multiple Linux servers
- Password-based SSH authentication
- Encrypted credential storage
- Automatic Linux distribution discovery
- Automatic privilege escalation detection
- Check for available package updates
- Install selected updates
- Install all available updates
- Package cleanup
- Detect whether a reboot is required
- Display why a reboot is required
- Persistent update history
- Configurable history retention
- Scheduled update tasks
- Multi-server task targets
- Dark web interface with green accent theme

## Security Scope

PatchForge intentionally provides a very limited remote-management surface.

It can perform only predefined package-management operations required for Linux update management.

PatchForge does **not** provide:

- Remote reboot
- Shutdown
- Shell access
- Interactive terminal access
- Arbitrary command execution
- Custom scripts
- User-defined remote commands

A reboot may be detected and displayed, but it cannot be triggered from PatchForge.

## Supported Package Managers

### Version 1.1.0

- APT

The initial release focuses on Debian/Ubuntu-style APT systems.

Support for additional package managers may be added in future releases.

## Docker Installation

Clone the repository:

```bash
git clone https://github.com/Mauckisch/patchforge.git
cd patchforge
```

Start PatchForge:

```bash
docker compose pull
docker compose up -d
```

Open PatchForge in a browser:

```text
http://<docker-host>:7338
```

## Updating PatchForge

```bash
docker compose pull
docker compose up -d
```

## Docker Image

The production Docker Compose configuration uses:

```text
ghcr.io/mauckisch/patchforge:latest
```

## Persistent Data

Runtime data is stored in:

```text
./data
```

This includes the PatchForge database and locally generated application secrets.

Runtime data and secrets are excluded from Git.

Back up the `data` directory if you want to preserve the PatchForge configuration.

## Port

Default host port:

```text
7338
```

Container port:

```text
8080
```

## History Retention

PatchForge stores update-management history persistently.

The default retention period is **7 days**.

The retention period can be changed globally in the web interface. Automatic retention can also be disabled by selecting **Unlimited**.

## Development

Development-specific Docker Compose configuration is intentionally not included in the repository.

The public `docker-compose.yml` is intended for normal production use with the published container image.

## Project

GitHub: https://github.com/Mauckisch/patchforge
