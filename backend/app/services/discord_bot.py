"""QUARK Discord bot — chat with the assistant from a Discord channel.

Runs as its own process (``python -m app.services.discord_bot``), separate from
the FastAPI app, so it brings up its own MQTT connection and Redis pool. Incoming
messages are routed through the same ``quark_agent`` the HTTP chat uses, with
per-channel short-term memory, so home-control tool calls publish over MQTT too.
"""
from __future__ import annotations

import logging

import discord
import redis.asyncio as aioredis
from pydantic_ai.messages import ModelMessage

from app.agents.deps import QuarkDeps
from app.agents.quark_agent import quark_agent
from app.core.config import get_settings
from app.core.redis import get_pool
from app.routers.chat import _to_message_history
from app.services.memory import redis_append_conversation, redis_get_conversation
from app.services.mqtt_bridge import mqtt_bridge

logger = logging.getLogger(__name__)
settings = get_settings()

# Discord hard-caps a single message at 2000 characters.
_DISCORD_MAX = 2000


class QuarkDiscordClient(discord.Client):
    """Minimal Discord client that proxies messages to the QUARK agent."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self._redis: aioredis.Redis | None = None

    async def setup_hook(self) -> None:
        await mqtt_bridge.start()
        self._redis = aioredis.Redis(connection_pool=get_pool())

    async def on_ready(self) -> None:
        logger.info("QUARK Discord bot connected as %s", self.user)

    def _should_handle(self, message: discord.Message) -> bool:
        if self.user is not None and message.author.id == self.user.id:
            return False
        if message.author.bot:
            return False
        channel_id = settings.discord_channel_id
        if channel_id and str(message.channel.id) != str(channel_id):
            return False
        return bool(message.content.strip())

    async def on_message(self, message: discord.Message) -> None:
        if not self._should_handle(message):
            return

        content = message.content.strip()
        session_id = f"discord:{message.channel.id}"
        redis = self._redis
        deps = QuarkDeps(mqtt=mqtt_bridge, redis=redis)

        history: list[ModelMessage] = []
        if redis is not None:
            turns = await redis_get_conversation(redis, session_id)
            history = _to_message_history(turns)
            await redis_append_conversation(redis, session_id, "user", content)

        try:
            async with message.channel.typing():
                result = await quark_agent.run(content, message_history=history, deps=deps)
        except Exception:
            logger.exception("Agent run failed for Discord message in %s", session_id)
            await message.channel.send("미안, 지금 응답 처리에 문제가 생겼어. 잠깐 뒤에 다시 해줄래?")
            return

        reply = result.output
        if redis is not None:
            await redis_append_conversation(redis, session_id, "assistant", reply)
        await message.channel.send(reply[:_DISCORD_MAX])


def main() -> None:
    settings = get_settings()
    token = settings.discord_token
    if not token:
        raise RuntimeError("discord_token is not configured (secrets/discord_token)")
    logging.basicConfig(level=settings.log_level.upper())
    client = QuarkDiscordClient()
    client.run(token, log_handler=None)


if __name__ == "__main__":
    main()
