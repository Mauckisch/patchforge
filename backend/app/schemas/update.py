from pydantic import BaseModel, Field


class InstallUpdatesRequest(BaseModel):
    packages: list[str] = Field(
        min_length=1,
        max_length=500,
    )
