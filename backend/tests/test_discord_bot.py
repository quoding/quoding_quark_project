"""The Discord bot routes a message through the agent and replies (no live LLM)."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from fakeredis import aioredis as fake_aioredis
from pydantic_ai.models.test import TestModel

from app.agents.quark_agent import quark_agent
from app.services.discord_bot import QuarkDiscordClient


class _Typing:
    async def __aenter__(self) -> _Typing:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False


class _FakeChannel:
    def __init__(self) -> None:
        self.id = 4242
        self.send = AsyncMock()

    def typing(self) -> _Typing:
        return _Typing()


class _FakeAuthor:
    def __init__(self) -> None:
        self.id = 1
        self.bot = False


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.author = _FakeAuthor()
        self.channel = _FakeChannel()
        self.content = content


async def test_on_message_replies_via_agent(fake_redis: fake_aioredis.FakeRedis) -> None:
    client = QuarkDiscordClient()
    client._redis = fake_redis  # skip setup_hook (no MQTT/real redis in test)

    message = _FakeMessage("안녕 쿼크")
    with quark_agent.override(model=TestModel(call_tools=[])):
        await client.on_message(message)  # type: ignore[arg-type]

    message.channel.send.assert_awaited_once()
    reply = message.channel.send.await_args.args[0]
    assert isinstance(reply, str) and reply

    # Conversation memory captured both turns under the per-channel session.
    from app.services.memory import redis_get_conversation

    conv = await redis_get_conversation(fake_redis, "discord:4242")
    roles = [t["role"] for t in conv]
    assert "user" in roles and "assistant" in roles


async def test_on_message_ignores_bots(fake_redis: fake_aioredis.FakeRedis) -> None:
    client = QuarkDiscordClient()
    client._redis = fake_redis

    message = _FakeMessage("무시해줘")
    message.author.bot = True
    await client.on_message(message)  # type: ignore[arg-type]

    cast_channel: Any = message.channel
    cast_channel.send.assert_not_awaited()
