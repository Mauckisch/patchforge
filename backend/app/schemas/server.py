from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ServerCreate(BaseModel):
    name: str | None = Field(
        default=None,
        max_length=100,
    )

    use_system_hostname: bool = False
    use_fqdn: bool = False


    host: str = Field(
        min_length=1,
        max_length=255,
    )

    ssh_port: int = Field(
        default=22,
        ge=1,
        le=65535,
    )

    username: str = Field(
        min_length=1,
        max_length=100,
    )


class ServerUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        max_length=100,
    )

    use_system_hostname: bool | None = None
    use_fqdn: bool | None = None

    host: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    ssh_port: int | None = Field(
        default=None,
        ge=1,
        le=65535,
    )

    username: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )


class ServerResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    name: str
    host: str
    ssh_port: int
    username: str

    use_system_hostname: bool
    use_fqdn: bool
    system_hostname: str | None

    distribution: str | None
    distribution_version: str | None
    package_manager: str | None
    architecture: str | None
    kernel_version: str | None

    reboot_required: bool
    cleanup_available: bool | None

    connection_status: str
    updates_available: int

    operation_status: str
    operation_type: str | None
    operation_progress: int
    operation_current: int
    operation_total: int
    operation_current_package: str | None
    operation_message: str | None
    operation_started_at: datetime | None

    last_seen_at: datetime | None
    updates_checked_at: datetime | None
    last_check_at: datetime | None
    last_error: str | None

    created_at: datetime
    updated_at: datetime


class HostnamePreviewResponse(BaseModel):
    hostname: str
    fqdn: str
    domain: str
