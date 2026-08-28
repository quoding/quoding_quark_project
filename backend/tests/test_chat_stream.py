"""SSE chat endpoint streams real agent deltas and persists conversation memory."""
from __future__ import annotations

import datetime as _dt
import json
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fakeredis import aioredis as fake_aioredis
from pydantic_ai.models.test import TestModel

from app.agents.quark_agent import quark_agent
from app.core.database import get_db
from app.core.redis import get_redis
from app.main import app
from app.models.chat import ChatConversation, ChatMessage
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


# ── /api/chat/sessions — DB-backed conversation list/history/delete ─────────


class _FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeResult:
        return self

    def all(self) -> list[Any]:
        return self._rows


class _FakeSession:
    def __init__(self, rows: list[Any] | None = None) -> None:
        self._rows = rows or []
        self.deleted: list[Any] = []
        self.get_return: Any | None = None

    async def execute(self, *_: Any, **__: Any) -> _FakeResult:
        return _FakeResult(self._rows)

    async def get(self, *_: Any, **__: Any) -> Any | None:
        return self.get_return

    async def delete(self, obj: Any) -> None:
        self.deleted.append(obj)


def _override_db(session: _FakeSession) -> Any:
    async def _fake_db() -> AsyncGenerator[_FakeSession, None]:
        yield session

    return _fake_db


async def test_list_sessions_returns_web_conversations() -> None:
    now = _dt.datetime(2026, 8, 26, 8, 0, tzinfo=_dt.UTC)
    convo = ChatConversation(session_id="s1", source="web", title="안녕 쿼크", updated_at=now)
    app.dependency_overrides[get_db] = _override_db(_FakeSession([convo]))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/chat/sessions")
        assert resp.status_code == 200
        body = resp.json()
        assert body == [{"session_id": "s1", "title": "안녕 쿼크", "updated_at": "2026-08-26T08:00:00Z"}]
    finally:
        app.dependency_overrides.clear()


async def test_get_session_messages_returns_ordered_turns() -> None:
    now = _dt.datetime(2026, 8, 26, 8, 0, tzinfo=_dt.UTC)
    messages = [
        ChatMessage(session_id="s1", role="user", content="안녕", created_at=now),
        ChatMessage(session_id="s1", role="assistant", content="안녕하세요", created_at=now),
    ]
    app.dependency_overrides[get_db] = _override_db(_FakeSession(messages))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/chat/sessions/s1/messages")
        assert resp.status_code == 200
        roles = [m["role"] for m in resp.json()]
        assert roles == ["user", "assistant"]
    finally:
        app.dependency_overrides.clear()


async def test_delete_session_removes_conversation() -> None:
    session = _FakeSession()
    session.get_return = ChatConversation(session_id="s1", source="web")
    app.dependency_overrides[get_db] = _override_db(session)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/chat/sessions/s1")
        assert resp.status_code == 204
        assert len(session.deleted) == 1
    finally:
        app.dependency_overrides.clear()


async def test_delete_session_missing_returns_404() -> None:
    session = _FakeSession()
    session.get_return = None
    app.dependency_overrides[get_db] = _override_db(session)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/chat/sessions/missing")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_chat_stream_persists_to_db_when_available() -> None:
    """persist_message is called for both turns when a real DB session is provided."""
    fake_redis = fake_aioredis.FakeRedis(decode_responses=True)

    async def _override_redis() -> Any:
        yield fake_redis

    db_session = AsyncMock()
    db_session.get = AsyncMock(return_value=None)
    db_session.add = MagicMock()

    async def _override_db_optional() -> AsyncGenerator[Any, None]:
        yield db_session

    from app.core.database import get_db_optional

    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_db_optional] = _override_db_optional
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    try:
        with quark_agent.override(model=TestModel(call_tools=[])):
            resp = await client.post(
                "/api/chat/stream",
                json={"session_id": "s2", "message": "안녕 쿼크"},
            )
        assert resp.status_code == 200
        # persist_message() calls db.get + db.add + db.commit for each turn (user, assistant)
        assert db_session.add.call_count >= 2
        assert db_session.commit.await_count >= 2
    finally:
        await client.aclose()
        app.dependency_overrides.clear()
