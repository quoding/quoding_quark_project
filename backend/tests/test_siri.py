"""Siri Shortcuts-facing /api/siri/ask endpoint: token auth, TTS cleanup, multi-turn memory."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fakeredis import aioredis as fake_aioredis

from app.core.redis import get_redis
from app.main import app
from app.routers.siri import _clean_for_speech
from app.services.memory import redis_get_conversation

_TEST_SIRI_KEY = "test-siri-key"
_AUTH_HEADERS = {"Authorization": f"Bearer {_TEST_SIRI_KEY}"}


def _patched_settings() -> SimpleNamespace:
    return SimpleNamespace(siri_api_key=_TEST_SIRI_KEY)


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


def test_clean_for_speech_strips_markdown_and_emoji() -> None:
    assert _clean_for_speech("**안녕** 오늘 일정은 _없어_ 👋😄") == "안녕 오늘 일정은 없어"


def test_clean_for_speech_strips_headers_and_collapses_blanks() -> None:
    assert _clean_for_speech("## 오늘의 요약\n\n- 할일:  청소") == "오늘의 요약\n\n- 할일: 청소"


async def test_siri_ask_requires_token(
    client_and_redis: tuple[httpx.AsyncClient, fake_aioredis.FakeRedis],
) -> None:
    client, _ = client_and_redis
    try:
        resp = await client.post("/api/siri/ask", json={"message": "안녕"})
        assert resp.status_code == 401
    finally:
        await client.aclose()
        app.dependency_overrides.clear()


async def test_siri_ask_rejects_wrong_token(
    client_and_redis: tuple[httpx.AsyncClient, fake_aioredis.FakeRedis],
) -> None:
    client, _ = client_and_redis
    try:
        with patch("app.core.auth.get_settings", return_value=_patched_settings()):
            resp = await client.post(
                "/api/siri/ask",
                json={"message": "안녕"},
                headers={"Authorization": "Bearer wrong-token"},
            )
        assert resp.status_code == 401
    finally:
        await client.aclose()
        app.dependency_overrides.clear()


async def test_siri_ask_returns_cleaned_agent_reply_and_persists_turns(
    client_and_redis: tuple[httpx.AsyncClient, fake_aioredis.FakeRedis],
) -> None:
    client, redis = client_and_redis
    fake_result = SimpleNamespace(output="**오늘** 일정은 없어요 😄")
    try:
        with (
            patch("app.core.auth.get_settings", return_value=_patched_settings()),
            patch("app.routers.siri.quark_agent.run", new=AsyncMock(return_value=fake_result)) as run_mock,
        ):
            resp = await client.post(
                "/api/siri/ask",
                json={"message": "오늘 일정 알려줘"},
                headers=_AUTH_HEADERS,
            )
        assert resp.status_code == 200
        assert resp.json() == {"reply": "오늘 일정은 없어요"}
        run_mock.assert_awaited_once()
        assert run_mock.await_args.args[0] == "오늘 일정 알려줘"

        conv = await redis_get_conversation(redis, "siri-default")
        roles = [turn["role"] for turn in conv]
        assert roles == ["user", "assistant"]
        assert conv[1]["content"] == "**오늘** 일정은 없어요 😄"  # 원문(마크다운 포함)을 그대로 저장 — 다음 턴 맥락용
    finally:
        await client.aclose()
        app.dependency_overrides.clear()


async def test_siri_ask_continues_conversation_across_calls(
    client_and_redis: tuple[httpx.AsyncClient, fake_aioredis.FakeRedis],
) -> None:
    """두 번째 호출은 첫 번째 턴의 history를 message_history로 받아야 한다 (세션 고정 — 단축어가 session_id를 안 보내도 이어짐)."""
    client, _ = client_and_redis
    try:
        with (
            patch("app.core.auth.get_settings", return_value=_patched_settings()),
            patch(
                "app.routers.siri.quark_agent.run",
                new=AsyncMock(side_effect=[SimpleNamespace(output="라이언이야"), SimpleNamespace(output="라이언 좋아해")]),
            ) as run_mock,
        ):
            await client.post("/api/siri/ask", json={"message": "내 최애 캐릭터가 뭐였지"}, headers=_AUTH_HEADERS)
            await client.post("/api/siri/ask", json={"message": "그 캐릭터 어때"}, headers=_AUTH_HEADERS)

        assert run_mock.await_count == 2
        second_call_history = run_mock.await_args_list[1].kwargs["message_history"]
        assert len(second_call_history) == 2  # 직전 user+assistant 턴이 message_history로 전달됨
    finally:
        await client.aclose()
        app.dependency_overrides.clear()
