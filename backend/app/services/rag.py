"""Long-term RAG memory: save, retrieve, daily summary, morning brief.

Rules:
- ``memory.py`` is WIP-locked — only import from it, never modify it.
- ``get_embedding`` is mocked in tests (``monkeypatch``).
- All DB ops are gracefully skipped when ``db`` is unavailable.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import AgentMemory, DailyEpisode
from app.services.embeddings import get_embedding
from app.services.memory import pgvector_search, redis_get_conversation, save_daily_summary

logger = logging.getLogger(__name__)


async def save_memory(content: str, meta: dict[str, Any], db: AsyncSession) -> None:
    """Embed *content* and persist an ``AgentMemory`` row."""
    embedding = await get_embedding(content)
    memory = AgentMemory(content=content, meta=meta, embedding=embedding)
    db.add(memory)
    await db.commit()


async def retrieve(query: str, db: AsyncSession, k: int = 5) -> list[dict[str, Any]]:
    """Return top-*k* memories most similar to *query*."""
    embedding = await get_embedding(query)
    results: list[dict[str, Any]] = await pgvector_search(db, embedding, limit=k)
    return results


async def create_daily_summary(
    session_id: str,
    redis: aioredis.Redis,
    db: AsyncSession,
) -> None:
    """Summarise the Redis conversation for *session_id* and upsert a daily episode."""
    turns = await redis_get_conversation(redis, session_id)
    if not turns:
        logger.debug("create_daily_summary: no turns for session %s", session_id)
        return

    conv_text = "\n".join(f"{t['role']}: {t['content']}" for t in turns)

    from app.agents.deps import QuarkDeps
    from app.agents.quark_agent import quark_agent
    from app.services.mqtt_bridge import mqtt_bridge

    result = await quark_agent.run(
        f"다음 대화를 한국어로 3줄로 요약해줘:\n\n{conv_text[:3000]}",
        deps=QuarkDeps(mqtt=mqtt_bridge),
    )
    await save_daily_summary(db, {"session_id": session_id, "text": result.output})
    logger.info("Daily summary saved for session %s", session_id)


async def create_morning_brief_content(db: AsyncSession) -> str:
    """Generate a morning briefing string using recent daily episodes."""
    eps_result = await db.execute(
        select(DailyEpisode).order_by(DailyEpisode.date.desc()).limit(3)
    )
    episodes = eps_result.scalars().all()

    ep_context: str
    if episodes:
        ep_context = "최근 일별 요약:\n" + "\n".join(
            f"- {e.date}: {str(e.summary.get('text', ''))[:200]}"
            for e in episodes
        )
    else:
        ep_context = "특별한 최근 기록 없음."

    from app.agents.deps import QuarkDeps
    from app.agents.quark_agent import quark_agent
    from app.services.mqtt_bridge import mqtt_bridge

    result = await quark_agent.run(
        f"오늘은 {date.today().isoformat()}이야. "
        "간결한 아침 브리핑을 2~3문장으로 한국어로 만들어줘.\n\n"
        f"{ep_context}",
        deps=QuarkDeps(mqtt=mqtt_bridge),
    )
    return result.output
