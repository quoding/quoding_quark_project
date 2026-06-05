from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Device(Base):
    """Registry of known IoT devices (lights, led, ac, plant, sensors, …)."""

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(32))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }
