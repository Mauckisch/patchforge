<p align="center">
  <img
    src="frontend/public/branding/patchforge-logo.svg"
    alt="PatchForge for Linux Logo"
    width="760"
  >
</p>

# PatchForge for Linux

PatchForge for Linux is a focused web application for managing package updates on Linux servers.

Current version: **1.5.1**

## Features

- Manage multiple Linux servers
- Password-based SSH authentication
- Encrypted credential storage
- Automatic Linux distribution discovery
- Automatic package manager detection
- Automatic privilege escalation detection
- Check for available package updates
- Display available updates per server
- Install selected updates
- Install all available updates
- Detect available package cleanup
- Package cleanup
- Persist cleanup availability per server
- Detect whether a reboot is required
- Display why a reboot is required
- Persistent update history
- Configurable history retention
- Scheduled update tasks
- Multi-server task run tracking
- Aggregated scheduled-task notifications
- Per-server task run details
- Configurable notification-only-on-updates behavior
- Email and Discord notifications
- Multi-server task targets
- Central Settings page
- Configurable default task timezone
- Discord webhook notification configuration
- SMTP email notification configuration
- Encrypted storage of notification secrets
- Test Discord and email delivery without saving temporary test values
- Independent save and delete actions for notification channels
- Per-event notification channel preferences
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

PatchForge automatically detects the package manager of a managed Linux server.

### APT

APT support is available for Debian-based systems.

Supported operations:

- Refresh package metadata
- Check for available updates
- Detect held packages
- Install selected updates
- Install all available updates
- Detect removable package leftovers
- Package cleanup using APT autoremove/autoclean
- Detect whether a reboot is required

APT support has been tested with Debian-based systems, including Debian and Proxmox VE hosts.

### DNF

DNF support was introduced with **PatchForge 1.4.0**.

Supported operations:

- Refresh package metadata
- Check for available updates
- Install selected updates
- Install all available updates
- Detect unneeded packages
- Package cleanup using DNF
- Detect whether a reboot is required
- Detect running and installed kernel state

DNF support has been tested with **Oracle Linux 10.2**.

Other DNF-based distributions may work, but are not currently considered validated platforms.

## Notifications

PatchForge includes configurable notification transports for Discord and email.

Notification settings are managed from the **Settings** page in the web interface.

### Discord

Discord notifications use an incoming webhook.

The Discord configuration supports:

- Enable or disable the Discord notification channel
- Secure storage of the webhook URL
- Test messages using the current form values without automatically saving them
- Explicit saving of the Discord configuration
- Complete deletion of the stored Discord configuration

### Email

Email notifications use SMTP.

The email configuration supports:

- SMTP hostname and port
- No encryption, STARTTLS, or direct TLS/SSL
- Optional SMTP authentication
- Configurable sender address
- One or more recipients
- Secure storage of the SMTP password
- Test messages using the current form values without automatically saving them
- Explicit saving of the email configuration
- Complete deletion of the stored email configuration

Stored SMTP passwords and Discord webhook URLs are encrypted using the PatchForge application master key.

### Notification Events

The Settings page contains per-event preferences for email and Discord channels, including server status, package updates, cleanup, reboot-required state, installations, and scheduled tasks.

The event preferences define which notification channels should be used as event delivery is integrated into the corresponding PatchForge operations.

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
