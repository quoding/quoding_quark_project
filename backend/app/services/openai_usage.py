"""OpenAI usage API with daily cache (resets at midnight)."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {}


def _today_str() -> str:
    import datetime as _dt

    return _dt.date.today().isoformat()


async def get_openai_usage() -> dict[str, Any]:
    """Fetch today's OpenAI usage. Daily cache (resets after midnight)."""
    today = _today_str()
    if _cache.get("date") == today and "data" in _cache:
        return _cache["data"]

    settings = get_settings()
    token = settings.openai_api_key
    if not token:
        return {"error": "no_api_key"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.openai.com/v1/usage",
                params={"date": today},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()

        # Aggregate by model
        model_totals: dict[str, dict[str, Any]] = {}
        for entry in data.get("data", []):
            model = entry.get("snapshot_id", "unknown")
            prompt = entry.get("n_context_tokens_total", 0)
            completion = entry.get("n_generated_tokens_total", 0)
            if model not in model_totals:
                model_totals[model] = {"prompt": 0, "completion": 0}
            model_totals[model]["prompt"] += prompt
            model_totals[model]["completion"] += completion

        result: dict[str, Any] = {
            "date": today,
            "models": [
                {
                    "name": m,
                    "prompt_tokens": v["prompt"],
                    "completion_tokens": v["completion"],
                    "total_tokens": v["prompt"] + v["completion"],
                }
                for m, v in model_totals.items()
            ],
        }
        _cache["date"] = today
        _cache["data"] = result
        return result

    except Exception as exc:
        logger.warning("OpenAI usage fetch failed: %s", exc)
        return {"error": str(exc)}
