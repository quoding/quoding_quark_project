"""Discord REST 발송 헬퍼 — gateway 없이 채널에 메시지를 보낸다.

scheduler/rule_router 등 봇 프로세스 밖에서도 알림을 보낼 수 있도록
bot 토큰 + 채널 ID로 REST API를 직접 호출한다.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_DISCORD_MAX = 2000


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
