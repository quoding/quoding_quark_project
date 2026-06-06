"""Docker container stats via docker SDK with 10-second cache."""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {}
_CACHE_TTL = 10.0


def _cached() -> list[dict[str, Any]] | None:
    if _cache.get("ts") and time.monotonic() - _cache["ts"] < _CACHE_TTL:
        return _cache.get("data")
    return None


def get_docker_stats() -> list[dict[str, Any]]:
    """Return per-container CPU%, memory MB, and status (10s cache)."""
    cached = _cached()
    if cached is not None:
        return cached

    try:
        import docker  # type: ignore[import-untyped]

        client = docker.from_env()
        result: list[dict[str, Any]] = []

        for container in client.containers.list(all=True):
            entry: dict[str, Any] = {
                "name": container.name,
                "img": container.image.tags[0] if container.image.tags else container.image.short_id,
                "status": container.status,
                "cpu": 0.0,
                "mem": 0,
            }
            if container.status == "running":
                try:
                    raw = container.stats(stream=False)
                    cpu_delta = (
                        raw["cpu_stats"]["cpu_usage"]["total_usage"]
                        - raw["precpu_stats"]["cpu_usage"]["total_usage"]
                    )
                    sys_delta = (
                        raw["cpu_stats"]["system_cpu_usage"]
                        - raw["precpu_stats"]["system_cpu_usage"]
                    )
                    num_cpus = raw["cpu_stats"].get("online_cpus") or len(
                        raw["cpu_stats"]["cpu_usage"].get("percpu_usage", [1])
                    )
                    cpu_pct = (cpu_delta / sys_delta) * num_cpus * 100.0 if sys_delta > 0 else 0.0
                    mem_usage = raw["memory_stats"].get("usage", 0)
                    mem_cache = raw["memory_stats"].get("stats", {}).get("cache", 0)
                    mem_mb = round((mem_usage - mem_cache) / 1024 / 1024, 1)
                    entry["cpu"] = round(cpu_pct, 1)
                    entry["mem"] = mem_mb
                except Exception as exc:
                    logger.debug("Stats error for %s: %s", container.name, exc)
            result.append(entry)

        _cache["data"] = result
        _cache["ts"] = time.monotonic()
        return result

    except Exception as exc:
        logger.warning("Docker stats failed: %s", exc)
        return []
