"""Discord REST 발송 헬퍼 — gateway 없이 채널에 메시지를 보낸다.

scheduler/rule_router 등 봇 프로세스 밖에서도 알림을 보낼 수 있도록
bot 토큰 + 채널 ID로 REST API를 직접 호출한다.
"""
from __future__ import annotations

import logging

import httpx
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.redis import get_pool

logger = logging.getLogger(__name__)

_DISCORD_MAX = 2000
_DISCORD_TOGGLE_KEY = "quark:notify_discord_enabled"
_PUSH_TOGGLE_KEY = "quark:notify_push_enabled"


async def send_discord_message(content: str, channel_id: str | None = None) -> bool:
    """settings.discord_channel_id(또는 *channel_id*)로 *content*를 발송한다."""
    cfg = get_settings()
    channel = channel_id or cfg.discord_channel_id
    if not channel or not cfg.discord_token:
        logger.warning("Discord notify skipped: channel/token not configured")
        return False

    url = f"https://discord.com/api/v10/channels/{channel}/messages"
    headers = {
        "Authorization": f"Bot {cfg.discord_token}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, json={"content": content[:_DISCORD_MAX]}, headers=headers, timeout=10.0
            )
            resp.raise_for_status()
        return True
    except Exception:
        logger.warning("Discord notify failed", exc_info=True)
        return False


async def _toggle_get(key: str) -> bool:
    """Fail-open Redis-backed boolean toggle — same pattern as embeddings.is_embedding_enabled()."""
    redis = aioredis.Redis(connection_pool=get_pool())
    try:
        value = await redis.get(key)
        return value != "0"
    except Exception:
        return True
    finally:
        try:
            await redis.aclose()
        except Exception:
            pass


async def _toggle_set(key: str, enabled: bool) -> None:
    redis = aioredis.Redis(connection_pool=get_pool())
    try:
        await redis.set(key, "1" if enabled else "0")
    finally:
        await redis.aclose()


async def is_discord_notify_enabled() -> bool:
    return await _toggle_get(_DISCORD_TOGGLE_KEY)


async def set_discord_notify_enabled(enabled: bool) -> None:
    await _toggle_set(_DISCORD_TOGGLE_KEY, enabled)


async def is_push_notify_enabled() -> bool:
    return await _toggle_get(_PUSH_TOGGLE_KEY)


async def set_push_notify_enabled(enabled: bool) -> None:
    await _toggle_set(_PUSH_TOGGLE_KEY, enabled)


async def notify(content: str, *, title: str = "QUARK") -> None:
    """Send *content* through every notification channel the user has enabled.

    Fixed automations (scheduler.py cron jobs, rule_router.py MQTT rules) call
    this instead of talking to Discord/push directly, so the on/off toggles in
    the 설정 page control every automated notification from one place.
    """
    if await is_discord_notify_enabled():
        await send_discord_message(content)
    if await is_push_notify_enabled():
        try:
            from app.core.database import AsyncSessionLocal
            from app.services.push import send_to_all

            async with AsyncSessionLocal() as db:
                await send_to_all(db, title, content)
        except Exception:
            logger.warning("Push notify failed", exc_info=True)
