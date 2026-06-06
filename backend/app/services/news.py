"""RSS news fetcher with 30-minute cache."""
from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

FEEDS = [
    ("연합뉴스", "https://feeds.yna.co.kr/rss/news.xml"),
    ("전자신문 IT", "https://rss.etnews.com/Section901.xml"),
    ("한겨레", "https://www.hani.co.kr/rss/"),
]

_cache: dict[str, Any] = {}
_CACHE_TTL = 1800.0  # 30 minutes


def _parse_time(entry: Any) -> str:
    try:
        import time as _time

        t = entry.get("published_parsed")
        if t:
            import datetime as _dt

            dt = _dt.datetime(*t[:6])
            now = _dt.datetime.utcnow()
            diff = now - dt
            mins = int(diff.total_seconds() // 60)
            if mins < 60:
                return f"{mins}분 전"
            if mins < 1440:
                return f"{mins // 60}시간 전"
            return f"{mins // 1440}일 전"
    except Exception:
        pass
    return ""


def get_news() -> list[dict[str, Any]]:
    """Return latest 5 items per feed, deduped by URL (30min cache)."""
    if _cache.get("ts") and time.monotonic() - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    try:
        import feedparser  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("feedparser not installed")
        return []

    seen_urls: set[str] = set()
    items: list[dict[str, Any]] = []

    for tag, url in FEEDS:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if count >= 5:
                    break
                link = entry.get("link", "")
                if link in seen_urls:
                    continue
                seen_urls.add(link)
                items.append(
                    {
                        "tag": tag,
                        "title": entry.get("title", ""),
                        "src": feed.feed.get("title", tag),
                        "time": _parse_time(entry),
                        "url": link,
                    }
                )
                count += 1
        except Exception as exc:
            logger.warning("Feed %s failed: %s", url, exc)

    _cache["data"] = items
    _cache["ts"] = time.monotonic()
    return items
