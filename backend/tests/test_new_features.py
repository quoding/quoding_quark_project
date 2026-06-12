"""미구현 기능 구현분 테스트 — home state 캐시, 일일 요약, 수분 알림, 에스컬레이션."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis import aioredis as fake_aioredis
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.quark_agent import quark_agent
from app.services.mqtt_bridge import MqttBridge, MqttMessage
from app.services.rule_router import RuleRouter
from app.tools.home import get_home_state


# ── MQTT state cache + get_home_state ────────────────────────────────────────


async def test_dispatch_caches_last_payload_per_topic(mock_bridge: MqttBridge) -> None:
    await mock_bridge._dispatch(MqttMessage(topic="quark/sensor/plant-01/moisture", payload={"value": 55}))
    await mock_bridge._dispatch(MqttMessage(topic="quark/sensor/plant-01/moisture", payload={"value": 42}))
    snap = mock_bridge.state_snapshot()
    assert snap["quark/sensor/plant-01/moisture"] == {"value": 42}


async def test_get_home_state_returns_live_snapshot(ctx: Any, mock_bridge: MqttBridge) -> None:
    await mock_bridge._dispatch(MqttMessage(topic="quark/sensor/desk/temp", payload={"value": 24.5}))
    result = await get_home_state(ctx)
    assert result["state"]["quark/sensor/desk/temp"] == {"value": 24.5}


async def test_get_home_state_without_data_returns_note(ctx: Any) -> None:
    result = await get_home_state(ctx)
    assert "note" in result and "state" not in result


# ── save_daily_summary → daily_episodes ──────────────────────────────────────


async def test_save_daily_summary_targets_daily_episodes() -> None:
    from app.services.memory import save_daily_summary

    db = AsyncMock(spec=AsyncSession)
    await save_daily_summary(db, {"text": "오늘 요약"})
    sql = str(db.execute.await_args.args[0])
    assert "daily_episodes" in sql
    db.commit.assert_awaited_once()


# ── create_daily_summary_all ─────────────────────────────────────────────────


async def test_create_daily_summary_all_merges_sessions(
    fake_redis: fake_aioredis.FakeRedis,
) -> None:
    from app.services.memory import redis_append_conversation
    from app.services.rag import create_daily_summary_all

    await redis_append_conversation(fake_redis, "web-1", "user", "거실 불 켜줘")
    await redis_append_conversation(fake_redis, "siri-default", "user", "내일 일정 뭐야")

    db = AsyncMock(spec=AsyncSession)
    with quark_agent.override(model=TestModel(call_tools=[], custom_output_text="요약 완료")):
        saved = await create_daily_summary_all(fake_redis, db)

    assert saved is True
    db.execute.assert_awaited()


async def test_create_daily_summary_all_skips_when_empty(
    fake_redis: fake_aioredis.FakeRedis,
) -> None:
    from app.services.rag import create_daily_summary_all

    db = AsyncMock(spec=AsyncSession)
    saved = await create_daily_summary_all(fake_redis, db)
    assert saved is False
    db.execute.assert_not_awaited()


# ── low-moisture rule → Discord (cooldown) ───────────────────────────────────


async def test_low_moisture_rule_sends_discord_once_within_cooldown() -> None:
    router = RuleRouter()
    with patch("app.services.rule_router.mqtt_bridge") as bridge:
        bridge.subscribe = MagicMock()
        router.load_defaults()

    msg = MqttMessage(topic="quark/sensor/plant-01/moisture", payload={"value": 12})
    with patch("app.services.notify.send_discord_message", new=AsyncMock()) as send:
        await router._handle(msg)
        await router._handle(msg)  # 쿨다운 내 재발행 — 무시되어야 함
    assert send.await_count == 1
    assert "plant-01" in send.await_args.args[0]


async def test_high_moisture_does_not_alert() -> None:
    router = RuleRouter()
    with patch("app.services.rule_router.mqtt_bridge") as bridge:
        bridge.subscribe = MagicMock()
        router.load_defaults()

    msg = MqttMessage(topic="quark/sensor/plant-01/moisture", payload={"value": 80})
    with patch("app.services.notify.send_discord_message", new=AsyncMock()) as send:
        await router._handle(msg)
    send.assert_not_awaited()
