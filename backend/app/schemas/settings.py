from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    history_retention_days: int | None


class SettingsUpdate(BaseModel):
    history_retention_days: int | None = Field(
        default=7,
        ge=1,
        le=3650,
    )
