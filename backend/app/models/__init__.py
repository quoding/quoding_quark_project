"""SQLAlchemy ORM models.

Importing this package registers every model on ``Base.metadata`` so that
``create_all`` and Alembic autogenerate see the full schema.
"""
from __future__ import annotations

from app.models.agenda import Automation, Habit, Idea, Memo, Todo, WaterLog
from app.models.device import Device
from app.models.memory import AgentMemory, DailyEpisode
from app.models.research import ResearchNote

__all__ = [
    "AgentMemory",
    "Automation",
    "DailyEpisode",
    "Device",
    "Habit",
    "Idea",
    "Memo",
    "ResearchNote",
    "Todo",
    "WaterLog",
]
