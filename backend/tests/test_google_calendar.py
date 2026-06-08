"""Google Calendar service: access-token refresh + REST wrapper (all HTTP mocked)."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.services import google_calendar as gcal


def _settings_with_oauth() -> SimpleNamespace:
    return SimpleNamespace(
        google_oauth_client_id="cid",
        google_oauth_client_secret="csecret",
        google_calendar_refresh_token="rtoken",
    )


def _resp(json_data: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=json_data)
    return resp


class _FakeClient:
    def __init__(self, post_response: MagicMock, request_response: MagicMock | None = None) -> None:
        self._post_response = post_response
        self._request_response = request_response
        self.post_calls: list[dict[str, Any]] = []
        self.request_calls: list[tuple[Any, ...]] = []

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def post(self, url: str, **kwargs: Any) -> MagicMock:
        self.post_calls.append({"url": url, **kwargs})
        return self._post_response

    async def request(self, method: str, url: str, **kwargs: Any) -> MagicMock:
        self.request_calls.append((method, url, kwargs))
        assert self._request_response is not None
        return self._request_response


@pytest.fixture(autouse=True)
def _reset_token_cache() -> None:
    gcal._token_cache.clear()
    yield
    gcal._token_cache.clear()


async def test_get_access_token_requires_oauth_settings() -> None:
    with patch("app.services.google_calendar.get_settings", return_value=SimpleNamespace(
        google_oauth_client_id="", google_oauth_client_secret="", google_calendar_refresh_token="",
    )):
        with pytest.raises(gcal.GoogleCalendarError):
            await gcal._get_access_token()


async def test_get_access_token_caches_until_expiry() -> None:
    fake = _FakeClient(post_response=_resp({"access_token": "tok-1", "expires_in": 3600}))
    with (
        patch("app.services.google_calendar.get_settings", return_value=_settings_with_oauth()),
        patch("app.services.google_calendar.httpx.AsyncClient", return_value=fake),
    ):
        first = await gcal._get_access_token()
        second = await gcal._get_access_token()

    assert first == second == "tok-1"
    assert len(fake.post_calls) == 1  # second call served from cache


async def test_list_events_normalizes_items() -> None:
    fake = _FakeClient(
        post_response=_resp({"access_token": "tok", "expires_in": 3600}),
        request_response=_resp({
            "items": [
                {"id": "evt1", "summary": "회의", "start": {"dateTime": "2026-06-10T14:00:00+09:00"}, "end": {"dateTime": "2026-06-10T15:00:00+09:00"}},
                {"id": "evt2", "start": {"date": "2026-06-11"}, "end": {"date": "2026-06-12"}},
            ]
        }),
    )
    with (
        patch("app.services.google_calendar.get_settings", return_value=_settings_with_oauth()),
        patch("app.services.google_calendar.httpx.AsyncClient", return_value=fake),
    ):
        events = await gcal.list_events("2026-06-10T00:00:00+09:00", "2026-06-12T00:00:00+09:00")

    assert events == [
        {"id": "evt1", "title": "회의", "start": "2026-06-10T14:00:00+09:00", "end": "2026-06-10T15:00:00+09:00", "all_day": False},
        {"id": "evt2", "title": "(제목 없음)", "start": "2026-06-11", "end": "2026-06-12", "all_day": True},
    ]


async def test_list_events_normalizes_utc_offset_to_kst() -> None:
    """Google이 UTC('Z')로 돌려준 dateTime도 +09:00 표기로 통일되어야 한다 (프런트 문자열 슬라이싱 전제)."""
    fake = _FakeClient(
        post_response=_resp({"access_token": "tok", "expires_in": 3600}),
        request_response=_resp({
            "items": [
                {"id": "evt1", "summary": "회의", "start": {"dateTime": "2026-06-09T06:00:00Z"}, "end": {"dateTime": "2026-06-09T07:00:00Z"}},
            ]
        }),
    )
    with (
        patch("app.services.google_calendar.get_settings", return_value=_settings_with_oauth()),
        patch("app.services.google_calendar.httpx.AsyncClient", return_value=fake),
    ):
        events = await gcal.list_events("2026-06-09T00:00:00+09:00", "2026-06-10T00:00:00+09:00")

    assert events == [
        {"id": "evt1", "title": "회의", "start": "2026-06-09T15:00:00+09:00", "end": "2026-06-09T16:00:00+09:00", "all_day": False},
    ]


async def test_list_events_returns_empty_on_error() -> None:
    class _RaisingClient(_FakeClient):
        async def request(self, method: str, url: str, **kwargs: Any) -> MagicMock:
            raise RuntimeError("boom")

    fake = _RaisingClient(post_response=_resp({"access_token": "tok", "expires_in": 3600}))
    with (
        patch("app.services.google_calendar.get_settings", return_value=_settings_with_oauth()),
        patch("app.services.google_calendar.httpx.AsyncClient", return_value=fake),
    ):
        events = await gcal.list_events("2026-06-10T00:00:00+09:00", "2026-06-12T00:00:00+09:00")
    assert events == []


async def test_create_event_posts_summary_and_times() -> None:
    fake = _FakeClient(
        post_response=_resp({"access_token": "tok", "expires_in": 3600}),
        request_response=_resp({
            "id": "evt-new",
            "summary": "치과 예약",
            "start": {"dateTime": "2026-06-10T14:00:00+09:00"},
            "end": {"dateTime": "2026-06-10T15:00:00+09:00"},
        }),
    )
    with (
        patch("app.services.google_calendar.get_settings", return_value=_settings_with_oauth()),
        patch("app.services.google_calendar.httpx.AsyncClient", return_value=fake),
    ):
        result = await gcal.create_event("치과 예약", "2026-06-10T14:00:00+09:00")

    assert result["id"] == "evt-new"
    method, url, kwargs = fake.request_calls[0]
    assert method == "POST"
    assert url.endswith("/calendars/primary/events")
    body = kwargs["json"]
    assert body["summary"] == "치과 예약"
    assert body["start"]["dateTime"] == "2026-06-10T14:00:00+09:00"
    assert body["end"]["dateTime"] == "2026-06-10T15:00:00+09:00"


async def test_update_event_sends_only_provided_fields() -> None:
    fake = _FakeClient(
        post_response=_resp({"access_token": "tok", "expires_in": 3600}),
        request_response=_resp({"id": "evt1", "summary": "변경된 제목", "start": {"dateTime": "2026-06-10T16:00:00+09:00"}, "end": {"dateTime": "2026-06-10T17:00:00+09:00"}}),
    )
    with (
        patch("app.services.google_calendar.get_settings", return_value=_settings_with_oauth()),
        patch("app.services.google_calendar.httpx.AsyncClient", return_value=fake),
    ):
        await gcal.update_event("evt1", title="변경된 제목")

    method, url, kwargs = fake.request_calls[0]
    assert method == "PATCH"
    assert url.endswith("/calendars/primary/events/evt1")
    assert kwargs["json"] == {"summary": "변경된 제목"}


async def test_delete_event_calls_delete() -> None:
    fake = _FakeClient(
        post_response=_resp({"access_token": "tok", "expires_in": 3600}),
        request_response=_resp({}),
    )
    with (
        patch("app.services.google_calendar.get_settings", return_value=_settings_with_oauth()),
        patch("app.services.google_calendar.httpx.AsyncClient", return_value=fake),
    ):
        await gcal.delete_event("evt1")

    method, url, _kwargs = fake.request_calls[0]
    assert method == "DELETE"
    assert url.endswith("/calendars/primary/events/evt1")
