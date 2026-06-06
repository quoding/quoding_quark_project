from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
import redis.asyncio  # noqa: F401  — makes redis.asyncio available as attribute for fakeredis
from fakeredis import aioredis as fake_aioredis

from app.agents.deps import QuarkDeps
from app.services.mqtt_bridge import MqttBridge


@pytest.fixture
def mock_bridge() -> MqttBridge:
    """A real MqttBridge with ``publish`` replaced by an AsyncMock.

    ``cmd()`` keeps its real implementation so we verify the exact topic/payload
    contract the way it reaches the wire.
    """
    bridge = MqttBridge()
    bridge.publish = AsyncMock()  # type: ignore[method-assign]
    return bridge


@pytest.fixture
def ctx(mock_bridge: MqttBridge) -> Any:
    """A minimal stand-in for ``RunContext`` — tools only touch ``ctx.deps``."""
    return SimpleNamespace(deps=QuarkDeps(mqtt=mock_bridge))


@pytest.fixture
def fake_redis() -> fake_aioredis.FakeRedis:
    return fake_aioredis.FakeRedis(decode_responses=True)
