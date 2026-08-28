"""Web push — subscribe/test endpoints and send_test() service logic (no real network calls)."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.database import get_db
from app.main import app
from app.models.push import PushSubscription
from app.services.push import send_test
from pywebpush import WebPushException


class _FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeResult:
        return self

    def all(self) -> list[Any]:
        return self._rows


class _FakeSession:
    def __init__(self, rows: list[Any] | None = None) -> None:
        self._rows = rows or []
        self.executed: list[Any] = []

    async def execute(self, stmt: Any, *_: Any, **__: Any) -> _FakeResult:
        self.executed.append(stmt)
        return _FakeResult(self._rows)

    async def commit(self) -> None:
        pass


def _override(session: _FakeSession) -> Any:
    async def _fake_db() -> AsyncGenerator[_FakeSession, None]:
        yield session

    return _fake_db


# ── send_test() ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_test_counts_successful_sends() -> None:
    subs = [
        PushSubscription(id=1, endpoint="https://push.example.com/a", p256dh="p1", auth="a1"),
        PushSubscription(id=2, endpoint="https://push.example.com/b", p256dh="p2", auth="a2"),
    ]
    with patch("app.services.push.webpush_async", new_callable=AsyncMock) as mock_send:
        result = await send_test(_FakeSession(subs))
    assert mock_send.await_count == 2
    assert result == {"sent": 2, "removed": 0}


@pytest.mark.asyncio
async def test_send_test_drops_expired_subscription_on_410() -> None:
    subs = [PushSubscription(id=1, endpoint="https://push.example.com/gone", p256dh="p", auth="a")]
    resp = MagicMock(status=410)
    with patch(
        "app.services.push.webpush_async",
        new_callable=AsyncMock,
        side_effect=WebPushException("gone", response=resp),
    ):
        result = await send_test(_FakeSession(subs))
    assert result == {"sent": 0, "removed": 1}


@pytest.mark.asyncio
async def test_send_test_keeps_subscription_on_other_errors() -> None:
    subs = [PushSubscription(id=1, endpoint="https://push.example.com/x", p256dh="p", auth="a")]
    resp = MagicMock(status=500)
    with patch(
        "app.services.push.webpush_async",
        new_callable=AsyncMock,
        side_effect=WebPushException("server error", response=resp),
    ):
        result = await send_test(_FakeSession(subs))
    assert result == {"sent": 0, "removed": 0}


# ── router ──────────────────────────────────────────────────────────────────


async def test_public_key_endpoint() -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/push/public-key")
    assert resp.status_code == 200
    assert "key" in resp.json()


async def test_subscribe_endpoint_accepts_payload() -> None:
    app.dependency_overrides[get_db] = _override(_FakeSession())
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/push/subscribe",
                json={"endpoint": "https://push.example.com/z", "keys": {"p256dh": "p", "auth": "a"}},
            )
        assert resp.status_code == 204
    finally:
        app.dependency_overrides.clear()


async def test_status_endpoint_returns_count() -> None:
    app.dependency_overrides[get_db] = _override(_FakeSession([PushSubscription(id=1, endpoint="e", p256dh="p", auth="a")]))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/push/status")
        assert resp.json() == {"subscriptions": 1}
    finally:
        app.dependency_overrides.clear()
