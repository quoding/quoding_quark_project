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
from app.services.embeddings import get_embedding, is_embedding_enabled
from app.services.memory import pgvector_search, redis_get_conversation, save_daily_summary

logger = logging.getLogger(__name__)

_MIN_SIMILARITY = 0.35  # cosine similarity — 이보다 낮으면 무관한 기억으로 취급


async def save_memory(content: str, meta: dict[str, Any], db: AsyncSession) -> None:
    """Embed *content* and persist an ``AgentMemory`` row. No-op when embedding is toggled off."""
    if not await is_embedding_enabled():
        return
    embedding = await get_embedding(content)
    memory = AgentMemory(content=content, meta=meta, embedding=embedding)
    db.add(memory)
    await db.commit()


async def retrieve(query: str, db: AsyncSession, k: int = 5) -> list[dict[str, Any]]:
    """Return top-*k* memories most similar to *query*. Empty when embedding is toggled off."""
    if not await is_embedding_enabled():
        return []
    embedding = await get_embedding(query)
    results: list[dict[str, Any]] = await pgvector_search(db, embedding, limit=k)
    # 임계값 미달 기억은 버린다 — top-k는 무관한 내용도 항상 반환하므로,
    # 그대로 주입하면 모든 대화에 노이즈 컨텍스트가 섞인다.
    return [r for r in results if r.get("similarity", 0.0) >= _MIN_SIMILARITY]


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


async def create_daily_summary_all(redis: aioredis.Redis, db: AsyncSession) -> bool:
    """오늘 Redis에 남아 있는 모든 세션(conv:*) 대화를 합쳐 하나의 일일 에피소드로 저장한다.

    스케줄러가 매일 밤 호출한다. 대화가 없으면 False를 반환하고 아무것도 저장하지 않는다.
    """
    session_ids: list[str] = []
    async for key in redis.scan_iter(match="conv:*"):
        name = key.decode() if isinstance(key, bytes) else key
        session_ids.append(name.split(":", 1)[1])

    blocks: list[str] = []
    for sid in sorted(session_ids):
        turns = await redis_get_conversation(redis, sid)
        if not turns:
            continue
        conv = "\n".join(f"{t['role']}: {t['content']}" for t in turns)
        blocks.append(f"[세션 {sid}]\n{conv}")

    if not blocks:
        logger.debug("create_daily_summary_all: no conversations today")
        return False

    conv_text = "\n\n".join(blocks)

    from app.agents.deps import QuarkDeps
    from app.agents.quark_agent import quark_agent
    from app.services.mqtt_bridge import mqtt_bridge

    result = await quark_agent.run(
        "다음은 오늘 하루 동안의 대화 기록이야. 오늘 무슨 일이 있었고 무엇을 했는지 "
        f"한국어 3~5줄로 요약해줘:\n\n{conv_text[:6000]}",
        deps=QuarkDeps(mqtt=mqtt_bridge),
    )
    await save_daily_summary(db, {"sessions": sorted(session_ids), "text": result.output})
    logger.info("Daily summary saved (%d sessions)", len(blocks))
    return True


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
