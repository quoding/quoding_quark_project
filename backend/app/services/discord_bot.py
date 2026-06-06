"""QUARK Discord bot — chat + reminders via slash commands.

Runs as its own process (``python -m app.services.discord_bot``).
Migrated to commands.Bot for Cog/slash-command support.
Existing per-channel chat functionality is fully preserved.
"""
from __future__ import annotations

import logging

import discord
from discord.ext import commands
from pydantic_ai.messages import ModelMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.deps import QuarkDeps
from app.agents.quark_agent import quark_agent
from app.agents.routing import build_model
from app.core.config import get_settings
from app.core.redis import get_pool
from app.models.reminder import Reminder
from app.routers.chat import _to_message_history
from app.services.memory import redis_append_conversation, redis_get_conversation
from app.services.mqtt_bridge import mqtt_bridge

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)
settings = get_settings()

_DISCORD_MAX = 2000


class QuarkBot(commands.Bot):
    """QUARK main bot — chat proxy + reminder dispatcher."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self._redis: aioredis.Redis | None = None
        self._db_factory: async_sessionmaker[AsyncSession] | None = None

    async def setup_hook(self) -> None:
        await mqtt_bridge.start()
        import redis.asyncio as aioredis_mod
        self._redis = aioredis_mod.Redis(connection_pool=get_pool())

        from app.core.database import AsyncSessionLocal
        self._db_factory = AsyncSessionLocal

        # Register bot instance into reminder_service before loading Cog
        from app.services import reminder_service
        reminder_service.set_bot(self)

        # Load reminder Cog
        await self.load_extension("app.discord.cogs.reminder")

        # Sync slash commands to Discord
        await self.tree.sync()
        logger.info("Slash commands synced")

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
        # Ignore slash-command interactions (they start with /)
        if message.content.startswith("/"):
            return False
        return bool(message.content.strip())

    async def on_message(self, message: discord.Message) -> None:
        # Let command framework process prefix commands first
        await self.process_commands(message)

        if not self._should_handle(message):
            return

        content = message.content.strip()
        session_id = f"discord:{message.channel.id}"
        redis = self._redis
        db: AsyncSession | None = None

        history: list[ModelMessage] = []
        if redis is not None:
            turns = await redis_get_conversation(redis, session_id)
            history = _to_message_history(turns)
            await redis_append_conversation(redis, session_id, "user", content)

        context_note = ""
        if self._db_factory is not None:
            try:
                async with self._db_factory() as db_session:
                    db = db_session
                    from app.services.rag import retrieve
                    memories = await retrieve(content, db_session, k=3)
                    if memories:
                        lines = "\n".join(f"- {m['content']}" for m in memories)
                        context_note = f"\n\n[관련 기억]\n{lines}"
            except Exception:
                logger.warning("Discord RAG retrieve failed", exc_info=True)
                db = None

        prompt = content + context_note
        model = build_model(content)
        deps = QuarkDeps(mqtt=mqtt_bridge, redis=redis, db=db)

        try:
            async with message.channel.typing():
                result = await quark_agent.run(
                    prompt, message_history=history, deps=deps, model=model
                )
        except Exception:
            logger.exception("Agent run failed for Discord message in %s", session_id)
            await message.channel.send("미안, 지금 응답 처리에 문제가 생겼어. 잠깐 뒤에 다시 해줄래?")
            return

        reply = result.output
        if redis is not None:
            await redis_append_conversation(redis, session_id, "assistant", reply)
        await message.channel.send(reply[:_DISCORD_MAX])

    # ── Reminder dispatch (called by reminder_service) ────────────────────────

    async def send_reminder(self, reminder: Reminder) -> None:
        """알림 메시지를 Discord 채널 또는 DM으로 발송."""
        from app.discord.cogs.reminder import ReminderView

        view = ReminderView(reminder_id=reminder.id)
        embed = discord.Embed(
            title="⏰ 알림",
            description=reminder.content,
            color=discord.Color.blurple(),
        )
        if reminder.cron_expr:
            embed.set_footer(text="🔁 반복 알림")

        # 채널 우선, 없으면 DM
        channel_id = reminder.discord_channel_id or settings.discord_reminder_channel_id
        sent = False

        if channel_id:
            ch = self.get_channel(int(channel_id))
            if ch is not None and isinstance(ch, discord.abc.Messageable):
                msg = await ch.send(
                    content=f"<@{reminder.discord_user_id}>",
                    embed=embed,
                    view=view,
                )
                view.message = msg
                sent = True

        if not sent:
            try:
                user = await self.fetch_user(int(reminder.discord_user_id))
                msg = await user.send(embed=embed, view=view)
                view.message = msg
            except discord.Forbidden:
                logger.warning(
                    "Cannot DM user %s for reminder %d", reminder.discord_user_id, reminder.id
                )


def main() -> None:
    token = settings.discord_token
    if not token:
        raise RuntimeError("discord_token is not configured (secrets/discord_token)")
    logging.basicConfig(level=settings.log_level.upper())
    bot = QuarkBot()
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()
