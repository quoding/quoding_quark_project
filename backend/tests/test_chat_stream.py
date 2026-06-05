"""SSE chat endpoint streams real agent deltas and persists conversation memory."""
from __future__ import annotations

import json

import httpx
import pytest
from fakeredis import aioredis as fake_aioredis
from pydantic_ai.models.test import TestModel

from app.agents.quark_agent import quark_agent
from app.core.redis import get_redis
from app.main import app
from app.services.memory import redis_get_conversation


@pytest.fixture
def client_and_redis(
    fake_redis: fake_aioredis.FakeRedis,
) -> tuple[httpx.AsyncClient, fake_aioredis.FakeRedis]:
    async def _override_redis() -> object:
        yield fake_redis

    app.dependency_overrides[get_redis] = _override_redis
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    return client, fake_redis


async def test_chat_stream_emits_deltas_and_persists(
    client_and_redis: tuple[httpx.AsyncClient, fake_aioredis.FakeRedis],
) -> None:
    client, redis = client_and_redis
    try:
        with quark_agent.override(model=TestModel(call_tools=[])):
            resp = await client.post(
                "/api/chat/stream",
                json={"session_id": "s1", "message": "안녕 쿼크"},
            )
        assert resp.status_code == 200
        body = resp.text

        # SSE frames present, including the terminating done frame.
        assert "data:" in body
        assert '"done": true' in body

        deltas = [
            json.loads(line[6:]).get("delta")
            for line in body.splitlines()
            if line.startswith("data: ") and "delta" in line
        ]
        assert any(deltas), "expected at least one streamed delta"

        # Conversation memory has both turns.
        conv = await redis_get_conversation(redis, "s1")
        roles = [turn["role"] for turn in conv]
        assert "user" in roles
        assert "assistant" in roles
    finally:
        await client.aclose()
        app.dependency_overrides.clear()
