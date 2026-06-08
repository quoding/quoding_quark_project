"""Google Calendar API v3 async wrapper — single source of truth for QUARK 일정.

OAuth refresh_token으로 액세스 토큰을 자동 갱신하며 (httpx, weather/github_stats와 동일한
패턴), 모든 호출은 사용자의 기본 캘린더(``primary``)를 대상으로 한다. 별도 로컬 DB
미러 테이블 없이 이 모듈을 통해서만 일정을 읽고 쓴다 — 양방향 동기화/충돌 해결을
피하기 위한 의도적인 설계.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_API_BASE = "https://www.googleapis.com/calendar/v3"
_CALENDAR_ID = "primary"
_TIMEZONE = "Asia/Seoul"
_KST = timezone(timedelta(hours=9))

_token_cache: dict[str, Any] = {}


class GoogleCalendarError(RuntimeError):
    """Google Calendar 호출 실패 (설정 누락 포함)."""


async def _get_access_token() -> str:
    cached = _token_cache.get("token")
    expires_at = _token_cache.get("expires_at", 0.0)
    if cached and time.monotonic() < expires_at:
        return cached

    settings = get_settings()
    if not (
        settings.google_oauth_client_id
        and settings.google_oauth_client_secret
        and settings.google_calendar_refresh_token
    ):
        raise GoogleCalendarError("Google Calendar 연동 설정 없음 (secrets/google_oauth_*, google_calendar_refresh_token)")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            _TOKEN_ENDPOINT,
            data={
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "refresh_token": settings.google_calendar_refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        payload = resp.json()

    token: str = payload["access_token"]
    _token_cache["token"] = token
    _token_cache["expires_at"] = time.monotonic() + payload.get("expires_in", 3600) - 60
    return token


async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    token = await _get_access_token()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.request(
            method,
            f"{_API_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            **kwargs,
        )
        resp.raise_for_status()
        return resp


def _to_kst_iso(value: str | None) -> str | None:
    """Google이 UTC('Z')·다른 오프셋으로 돌려준 dateTime을 +09:00로 통일한다.

    프런트가 문자열 슬라이싱(``.slice(11, 16)`` 등)으로 시각을 직접 추출하므로,
    오프셋이 항상 +09:00로 고정되어야 한다. 종일 일정의 'date'(YYYY-MM-DD)는 그대로 둔다.
    """
    if value is None or len(value) <= 10:
        return value
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.astimezone(_KST).isoformat()


def _to_event_dict(item: dict[str, Any]) -> dict[str, Any]:
    start = item.get("start", {})
    end = item.get("end", {})
    return {
        "id": item["id"],
        "title": item.get("summary") or "(제목 없음)",
        "start": _to_kst_iso(start.get("dateTime") or start.get("date")),
        "end": _to_kst_iso(end.get("dateTime") or end.get("date")),
        "all_day": "date" in start,
    }


def _time_payload(iso_dt: str) -> dict[str, str]:
    """naive/aware ISO datetime 문자열을 Google Calendar의 start/end 객체로 변환한다."""
    dt = datetime.fromisoformat(iso_dt)
    if dt.tzinfo is not None:
        return {"dateTime": dt.isoformat()}
    return {"dateTime": dt.isoformat(), "timeZone": _TIMEZONE}


async def list_events(time_min: str, time_max: str) -> list[dict[str, Any]]:
    """``time_min``~``time_max``(ISO 8601) 사이의 일정을 시작 시간순으로 반환한다."""
    try:
        resp = await _request(
            "GET",
            f"/calendars/{_CALENDAR_ID}/events",
            params={
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": "true",
                "orderBy": "startTime",
            },
        )
        items = resp.json().get("items", [])
        return [_to_event_dict(item) for item in items]
    except Exception as exc:
        logger.warning("Google Calendar list_events failed: %s", exc)
        return []


async def create_event(title: str, start: str, end: str | None = None) -> dict[str, Any]:
    """일정을 생성한다. ``end`` 생략 시 시작 시간 + 1시간으로 설정된다."""
    if end is None:
        start_dt = datetime.fromisoformat(start)
        end = (start_dt + timedelta(hours=1)).isoformat()

    resp = await _request(
        "POST",
        f"/calendars/{_CALENDAR_ID}/events",
        json={"summary": title, "start": _time_payload(start), "end": _time_payload(end)},
    )
    return _to_event_dict(resp.json())


async def update_event(
    event_id: str,
    *,
    title: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, Any]:
    """일정을 부분 수정한다 (PATCH — 넘긴 필드만 변경)."""
    body: dict[str, Any] = {}
    if title is not None:
        body["summary"] = title
    if start is not None:
        body["start"] = _time_payload(start)
    if end is not None:
        body["end"] = _time_payload(end)

    resp = await _request("PATCH", f"/calendars/{_CALENDAR_ID}/events/{event_id}", json=body)
    return _to_event_dict(resp.json())


async def delete_event(event_id: str) -> None:
    """일정을 삭제한다."""
    await _request("DELETE", f"/calendars/{_CALENDAR_ID}/events/{event_id}")
