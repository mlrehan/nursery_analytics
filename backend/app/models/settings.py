"""Single-row white-label app settings."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    brand_name: Mapped[str] = mapped_column(String(120), default="Nursery Analytics")
    brand_tagline: Mapped[str | None] = mapped_column(String(160))
    logo_url: Mapped[str | None] = mapped_column(Text)
    icon_url: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
