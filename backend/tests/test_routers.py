"""Health, route table, and devices router behaviour."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

import app.main
from app.core.database import get_db
from app.main import app
from app.routers import devices as devices_router

_TEST_SIRI_KEY = "test-siri-key"
_AUTH_HEADERS = {"Authorization": f"Bearer {_TEST_SIRI_KEY}"}


def test_required_routes_exist() -> None:
    paths = {getattr(r, "path", "") for r in app.routes}
    for required in ("/health", "/api/chat/stream", "/api/devices/cmd", "/api/devices"):
        assert required in paths, f"missing route {required}"


async def test_health_ok() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_devices_cmd_requires_siri_token() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/devices/cmd",
            json={"device_id": "light", "metric": "living", "value": False},
        )
    assert resp.status_code == 401


async def test_devices_cmd_publishes(monkeypatch: pytest.MonkeyPatch) -> None:
    cmd_mock = AsyncMock()
    monkeypatch.setattr(devices_router.mqtt_bridge, "cmd", cmd_mock)

    with patch("app.core.auth.get_settings", return_value=SimpleNamespace(siri_api_key=_TEST_SIRI_KEY)):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/devices/cmd",
                json={"device_id": "light", "metric": "living", "value": False},
                headers=_AUTH_HEADERS,
            )
    assert resp.status_code == 200
    cmd_mock.assert_awaited_once_with("light", "living", False)


async def test_devices_list_empty() -> None:
    class _Scalars:
        def all(self) -> list[Any]:
            return []

    class _Result:
        def scalars(self) -> _Scalars:
            return _Scalars()

    class _Session:
        async def execute(self, *args: Any, **kwargs: Any) -> _Result:
            return _Result()

    async def _fake_db() -> AsyncGenerator[_Session, None]:
        yield _Session()

    app.dependency_overrides[get_db] = _fake_db
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/devices")
        assert resp.status_code == 200
        assert resp.json() == {"devices": []}
    finally:
        app.dependency_overrides.clear()
