from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
    )

    # None = Unlimited
    history_retention_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=7,
    )
