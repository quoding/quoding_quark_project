from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Embedding dimension — matches OpenAI text-embedding-3-small (1536).
EMBEDDING_DIM = 1536


class AgentMemory(Base):
    """Long-term semantic memory for RAG (pgvector).

    Table name must stay ``agent_memories`` — ``app/services/memory.py`` issues
    raw SQL against it.
    """

    __tablename__ = "agent_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text)
    # Attribute renamed to ``meta`` because ``metadata`` is reserved on the
    # declarative base; the underlying column stays ``metadata``.
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyEpisode(Base):
    """One summarised episode per day.

    Table name must stay ``daily_episodes`` — see ``app/services/memory.py``.
    """

    __tablename__ = "daily_episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
