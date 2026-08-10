from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


TaskAction = Literal[
    "CHECK",
    "INSTALL_ALL",
    "CLEANUP",
    "REBOOT_CHECK",
]

ScheduleType = Literal[
    "once",
    "daily",
    "weekly",
    "monthly",
]


class TaskCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )

    server_ids: list[int] = Field(
        min_length=1,
        max_length=500,
    )

    action: TaskAction
    schedule_type: ScheduleType

    timezone: str = Field(
        default="UTC",
        min_length=1,
        max_length=100,
    )

    run_at: datetime | None = None

    hour: int | None = Field(
        default=None,
        ge=0,
        le=23,
    )

    minute: int | None = Field(
        default=None,
        ge=0,
        le=59,
    )

    weekday: int | None = Field(
        default=None,
        ge=0,
        le=6,
    )

    day_of_month: int | None = Field(
        default=None,
        ge=1,
        le=31,
    )

    enabled: bool = True

    @model_validator(mode="after")
    def validate_schedule(self):
        self.server_ids = list(
            dict.fromkeys(self.server_ids)
        )

        if self.schedule_type == "once":
            if self.run_at is None:
                raise ValueError(
                    "run_at is required for a one-time task"
                )

        elif self.schedule_type == "daily":
            if self.hour is None or self.minute is None:
                raise ValueError(
                    "hour and minute are required for a daily task"
                )

        elif self.schedule_type == "weekly":
            if (
                self.hour is None
                or self.minute is None
                or self.weekday is None
            ):
                raise ValueError(
                    "hour, minute and weekday are required "
                    "for a weekly task"
                )

        elif self.schedule_type == "monthly":
            if (
                self.hour is None
                or self.minute is None
                or self.day_of_month is None
            ):
                raise ValueError(
                    "hour, minute and day_of_month are required "
                    "for a monthly task"
                )

        return self


class TaskUpdate(TaskCreate):
    pass


class TaskResponse(BaseModel):
    id: int
    name: str

    server_ids: list[int]

    action: str
    schedule_type: str
    timezone: str

    run_at: datetime | None
    hour: int | None
    minute: int | None
    weekday: int | None
    day_of_month: int | None

    enabled: bool

    last_run_at: datetime | None
    next_run_at: datetime | None

    created_at: datetime
    updated_at: datetime
