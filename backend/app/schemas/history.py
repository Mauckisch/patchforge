from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: int
    server_name: str
    task_run_id: int | None
    action: str
    status: str
    package_count: int
    reboot_required: bool
    message: str | None
    created_at: datetime


class TaskRunHistoryResponse(BaseModel):
    id: int
    task_id: int
    task_name: str
    action: str
    status: str

    target_count: int
    success_count: int
    failed_count: int
    updates_found: int

    started_at: datetime
    completed_at: datetime | None
