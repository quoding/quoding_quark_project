"""Chat conversation history — durable Postgres store for the web chat UI.

Redis (``app/services/memory.py``: ``redis_append_conversation`` /
``redis_get_conversation``) remains the short-term (TTL) buffer the LLM reads
for message history. These tables are a separate, permanent record so past
conversations can be listed and reopened from the web UI.
"""
from __future__ import annotations

import datetime as _dt

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    session_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="web")
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        Text, ForeignKey("chat_conversations.session_id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
