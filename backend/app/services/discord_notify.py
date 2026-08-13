"""Shared Discord REST send helper — used by scheduler jobs and one-off services alike."""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


async def send_discord_message(channel_id: str, token: str, content: str) -> None:
    """Send *content* to a Discord channel using the bot REST API (no gateway)."""
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, json={"content": content[:2000]}, headers=headers, timeout=10.0
            )
            resp.raise_for_status()
        logger.info("Message sent to Discord channel %s", channel_id)
    except Exception:
        logger.warning("Discord send failed", exc_info=True)
