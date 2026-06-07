"""OpenAI text-embedding-3-small wrapper.

Import-safe without a live API key: the client is constructed per-call.
Tests mock this module via ``monkeypatch`` or ``unittest.mock.patch``.
"""
from __future__ import annotations

import openai
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.redis import get_pool

settings = get_settings()

_TOGGLE_KEY = "quark:embedding_enabled"


async def get_embedding(text: str) -> list[float]:
    """Return a 1536-dimensional embedding for *text* (text-embedding-3-small)."""
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key or "sk-no-key-configured")
    resp = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return list(resp.data[0].embedding)


async def is_embedding_enabled() -> bool:
    """RAG 임베딩 호출(저장/검색) 활성화 여부 — Redis에 영속화된 토글, 기본값 켜짐.

    Redis 연결 문제 시 fail-open(켜짐 취급) — 토글 자체가 임베딩 파이프라인을
    막는 새 장애점이 되어서는 안 된다.
    """
    redis = aioredis.Redis(connection_pool=get_pool())
    try:
        value = await redis.get(_TOGGLE_KEY)
        return value != "0"
    except Exception:
        return True
    finally:
        try:
            await redis.aclose()
        except Exception:
            pass


async def set_embedding_enabled(enabled: bool) -> None:
    redis = aioredis.Redis(connection_pool=get_pool())
    try:
        await redis.set(_TOGGLE_KEY, "1" if enabled else "0")
    finally:
        await redis.aclose()
