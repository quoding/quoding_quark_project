"""Internal service health checks with 5-second cache."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {}
_CACHE_TTL = 5.0


def _get_services() -> list[dict[str, Any]]:
    s = get_settings()
    return [
        {"name": "quark-api", "kind": "http", "url": "http://localhost:8000/health"},
        {"name": "postgres", "kind": "tcp", "host": s.postgres_host, "port": s.postgres_port},
        {"name": "redis", "kind": "tcp", "host": s.redis_host, "port": s.redis_port},
        {"name": "mosquitto", "kind": "tcp", "host": s.mqtt_host, "port": s.mqtt_port},
    ]


async def _check_http(url: str) -> tuple[str, int | None]:
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            t0 = time.monotonic()
            resp = await client.get(url)
            latency = round((time.monotonic() - t0) * 1000)
            if resp.status_code < 500:
                status = "warn" if latency > 200 else "up"
                return status, latency
            return "down", None
    except Exception:
        return "down", None


async def _check_tcp(host: str, port: int) -> tuple[str, int | None]:
    try:
        t0 = time.monotonic()
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=1.0
        )
        latency = round((time.monotonic() - t0) * 1000)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        status = "warn" if latency > 200 else "up"
        return status, latency
    except Exception:
        return "down", None


async def get_service_health() -> list[dict[str, Any]]:
    """Check all internal services and return health list (5s cache)."""
    if _cache.get("ts") and time.monotonic() - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    async def _probe(svc: dict[str, Any]) -> dict[str, Any]:
        if svc["kind"] == "http":
            status, latency = await _check_http(svc["url"])
        else:
            status, latency = await _check_tcp(svc["host"], svc["port"])
        return {"name": svc["name"], "status": status, "latency": latency}

    results = await asyncio.gather(*[_probe(s) for s in _get_services()])
    data = list(results)
    _cache["data"] = data
    _cache["ts"] = time.monotonic()
    return data
