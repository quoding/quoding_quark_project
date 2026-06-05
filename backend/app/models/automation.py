from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Automation(Base):
    """Persisted automation rule (mirrors the frontend ``Automation`` shape)."""

    __tablename__ = "automations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    trigger: Mapped[str] = mapped_column(String(256))
    action: Mapped[str] = mapped_column(String(256))
    on: Mapped[bool] = mapped_column(Boolean, default=True)
    runs: Mapped[int] = mapped_column(Integer, default=0)
    ico: Mapped[str] = mapped_column(String(32), default="automation")

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger": self.trigger,
            "action": self.action,
            "on": self.on,
            "runs": self.runs,
            "ico": self.ico,
        }
