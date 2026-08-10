from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ServerCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )

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
        min_length=1,
        max_length=100,
    )

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
    last_seen_at: datetime | None
    updates_checked_at: datetime | None
    last_check_at: datetime | None
    last_error: str | None

    created_at: datetime
    updated_at: datetime
