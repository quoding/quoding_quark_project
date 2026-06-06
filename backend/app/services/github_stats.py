"""GitHub contribution stats via GraphQL API with 1-hour cache."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {}
_CACHE_TTL = 3600.0  # 1 hour


def _get_token() -> str:
    secret_path = Path("/run/secrets/github_token")
    if secret_path.exists():
        return secret_path.read_text().strip()
    local_path = Path(__file__).parents[4] / "secrets" / "github_token"
    if local_path.exists():
        return local_path.read_text().strip()
    return ""


async def get_github_stats() -> dict[str, Any]:
    """Return streak, today/week commits from GitHub GraphQL (1h cache)."""
    if _cache.get("ts") and time.monotonic() - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    token = _get_token()
    if not token:
        return {"error": "no_token", "streak": 0, "today": 0, "week": 0, "lastCommit": "—"}

    import datetime as _dt

    today = _dt.date.today()
    from_date = (today - _dt.timedelta(days=365)).isoformat() + "T00:00:00"
    to_date = today.isoformat() + "T23:59:59"

    query = """
    query($from: DateTime!, $to: DateTime!) {
      viewer {
        login
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.github.com/graphql",
                json={"query": query, "variables": {"from": from_date, "to": to_date}},
                headers={"Authorization": f"bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()

        calendar = (
            data["data"]["viewer"]["contributionsCollection"]["contributionCalendar"]
        )
        weeks = calendar["weeks"]

        all_days: list[dict[str, Any]] = []
        for week in weeks:
            all_days.extend(week["contributionDays"])

        today_str = today.isoformat()
        week_start = (today - _dt.timedelta(days=today.weekday())).isoformat()

        today_count = 0
        week_count = 0
        last_commit_date = "—"
        streak = 0

        for day in reversed(all_days):
            d = day["date"]
            c = day["contributionCount"]
            if d == today_str:
                today_count = c
            if d >= week_start:
                week_count += c
            if c > 0 and last_commit_date == "—":
                last_commit_date = d

        # Calculate streak from today backwards
        for day in reversed(all_days):
            if day["date"] > today_str:
                continue
            if day["contributionCount"] > 0:
                streak += 1
            else:
                break

        result: dict[str, Any] = {
            "streak": streak,
            "today": today_count,
            "week": week_count,
            "lastCommit": last_commit_date,
        }
        _cache["data"] = result
        _cache["ts"] = time.monotonic()
        return result

    except Exception as exc:
        logger.warning("GitHub stats failed: %s", exc)
        return {"error": str(exc), "streak": 0, "today": 0, "week": 0, "lastCommit": "—"}
