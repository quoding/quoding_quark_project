from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

import redis.asyncio as aioredis
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Short-term: Redis (TTL 24h) ──────────────────────────────────────────────

async def redis_set(redis: aioredis.Redis, key: str, value: Any, ttl: int | None = None) -> None:
    raw = json.dumps(value)
    await redis.set(key, raw, ex=ttl or settings.redis_ttl_seconds)


async def redis_get(redis: aioredis.Redis, key: str) -> Any | None:
    raw = await redis.get(key)
    return json.loads(raw) if raw else None


async def redis_append_conversation(
    redis: aioredis.Redis, session_id: str, role: str, content: str
) -> None:
    key = f"conv:{session_id}"
    entry = json.dumps({"role": role, "content": content})
    await redis.rpush(key, entry)
    await redis.expire(key, settings.redis_ttl_seconds)


async def redis_get_conversation(redis: aioredis.Redis, session_id: str) -> list[dict]:
    key = f"conv:{session_id}"
    entries = await redis.lrange(key, 0, -1)
    return [json.loads(e) for e in entries]


def to_message_history(turns: list[dict[str, str]]) -> list[ModelMessage]:
    """Convert stored Redis turns into Pydantic AI message history."""
    history: list[ModelMessage] = []
    for turn in turns:
        content = turn.get("content", "")
        if turn.get("role") == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        else:
            history.append(ModelResponse(parts=[TextPart(content=content)]))
    return history


# ── Long-term: pgvector RAG ──────────────────────────────────────────────────

async def pgvector_search(
    db: AsyncSession, embedding: list[float], limit: int = 5
) -> list[dict]:
    result = await db.execute(
        text(
            "SELECT content, metadata, 1 - (embedding <=> CAST(:emb AS vector)) AS similarity "
            "FROM agent_memories "
            "ORDER BY embedding <=> CAST(:emb AS vector) "
            "LIMIT :limit"
        ),
        {"emb": str(embedding), "limit": limit},
    )
    return [{"content": r.content, "metadata": r.metadata, "similarity": r.similarity} for r in result]


# ── Episodic: daily JSON summaries ───────────────────────────────────────────

async def save_daily_summary(db: AsyncSession, summary: dict, day: date | None = None) -> None:
    day = day or date.today()
    await db.execute(
        text(
            "INSERT INTO daily_summaries (day, summary) VALUES (:day, :summary) "
            "ON CONFLICT (day) DO UPDATE SET summary = :summary"
        ),
        {"day": day.isoformat(), "summary": json.dumps(summary)},
    )
