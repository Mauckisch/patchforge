from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: int
    server_name: str
    action: str
    status: str
    package_count: int
    reboot_required: bool
    message: str | None
    created_at: datetime
