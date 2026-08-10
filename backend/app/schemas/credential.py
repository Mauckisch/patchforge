from typing import Literal

from pydantic import BaseModel, Field


PrivilegeMethod = Literal[
    "auto",
    "sudo",
    "su",
    "none",
]


class CredentialCreate(BaseModel):
    ssh_password: str = Field(
        min_length=1,
        max_length=1024,
    )

    privilege_method: PrivilegeMethod = "auto"

    privilege_password: str | None = Field(
        default=None,
        min_length=1,
        max_length=1024,
    )


class CredentialStatus(BaseModel):
    configured: bool
    privilege_method: PrivilegeMethod | None
    separate_privilege_password: bool
