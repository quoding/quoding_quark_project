"""Client for the QUARK host helper — a small process running outside Docker
on the mini PC host that performs operations the API container cannot do
itself (rebooting the host, broadcasting Wake-on-LAN packets onto the LAN).

See ``host-helper/`` at the repo root for the server side.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {get_settings().host_helper_token}"}


async def reboot_host() -> bool:
    """Ask the host helper to reboot the mini PC. Returns True on success."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.post(f"{settings.host_helper_base_url}/reboot", headers=_headers())
            resp.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.warning("host helper reboot failed: %s", exc)
            return False


async def wake_on_lan(mac: str) -> bool:
    """Ask the host helper to broadcast a WoL magic packet for ``mac``."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.post(
                f"{settings.host_helper_base_url}/wol", headers=_headers(), json={"mac": mac}
            )
            resp.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.warning("host helper wol failed: %s", exc)
            return False
