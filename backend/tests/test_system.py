"""Tests for system stats and weather endpoints."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.main import app
from app.services.system_stats import get_system_stats
from app.services.weather import _pm25_grade, _wmo_label, get_current_weather

# ── system stats ─────────────────────────────────────────────────────────────


def test_get_system_stats_keys() -> None:
    stats = get_system_stats()
    assert set(stats.keys()) >= {"cpu", "ram", "disk", "temp", "uptime_days"}
    assert isinstance(stats["cpu"], int)
    assert isinstance(stats["ram"], int)
    assert isinstance(stats["disk"], int)
    assert stats["temp"] is None or isinstance(stats["temp"], float)
    assert isinstance(stats["uptime_days"], int)


def test_get_system_stats_ranges() -> None:
    stats = get_system_stats()
    assert 0 <= stats["cpu"] <= 100
    assert 0 <= stats["ram"] <= 100
    assert 0 <= stats["disk"] <= 100
    assert stats["uptime_days"] >= 0


async def test_system_stats_endpoint() -> None:
    mock_stats = {"cpu": 30, "ram": 50, "disk": 60, "temp": 45.0, "uptime_days": 10}
    with patch("app.routers.system.get_system_stats", return_value=mock_stats):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/system/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cpu"] == 30
    assert data["uptime_days"] == 10


# ── weather helpers ───────────────────────────────────────────────────────────


def test_wmo_label_known_codes() -> None:
    assert _wmo_label(0) == "맑음"
    assert _wmo_label(61) == "가벼운 비"
    assert _wmo_label(95) == "뇌우"


def test_wmo_label_unknown() -> None:
    assert _wmo_label(999) == "알 수 없음"


def test_pm25_grade() -> None:
    assert _pm25_grade(10) == "좋음"
    assert _pm25_grade(25) == "보통"
    assert _pm25_grade(50) == "나쁨"
    assert _pm25_grade(100) == "매우나쁨"


# ── weather API mock ──────────────────────────────────────────────────────────


async def test_get_current_weather_success() -> None:
    weather_payload = {
        "current": {"temperature_2m": 22.5, "weather_code": 1},
        "daily": {"temperature_2m_max": [26.0], "temperature_2m_min": [16.0]},
    }
    aqi_payload = {"current": {"pm2_5": 12.0}}

    mock_weather_resp = MagicMock()
    mock_weather_resp.raise_for_status = MagicMock()
    mock_weather_resp.json.return_value = weather_payload

    mock_aqi_resp = MagicMock()
    mock_aqi_resp.raise_for_status = MagicMock()
    mock_aqi_resp.json.return_value = aqi_payload

    mock_geo_resp = MagicMock()
    mock_geo_resp.raise_for_status = MagicMock()
    mock_geo_resp.json.return_value = {"address": {"city": "구미시"}}

    call_count = 0

    async def mock_get(*_: Any, **__: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_weather_resp
        if call_count == 2:
            return mock_aqi_resp
        return mock_geo_resp

    class _FakeClient:
        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

        get = mock_get  # type: ignore[assignment]

    with patch("app.services.weather.httpx.AsyncClient", return_value=_FakeClient()):
        result = await get_current_weather()

    assert result["temp"] == 22.5
    assert result["label"] == "대체로 맑음"
    assert result["hi"] == 26.0
    assert result["lo"] == 16.0
    assert result["pm25"] == 12.0
    assert result["aqi_grade"] == "좋음"
    assert result["city"] == "구미시"


async def test_get_current_weather_failure() -> None:
    class _FailClient:
        async def __aenter__(self) -> _FailClient:
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

        async def get(self, *_: Any, **__: Any) -> None:
            raise ConnectionError("network error")

    with patch("app.services.weather.httpx.AsyncClient", return_value=_FailClient()):
        result = await get_current_weather()

    assert "error" in result


async def test_weather_endpoint_graceful_fallback() -> None:
    with patch("app.routers.system.get_current_weather", return_value={"error": "timeout"}):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/system/weather")
    assert resp.status_code == 200
    assert "error" in resp.json()


# ── minecraft afk (host helper) ──────────────────────────────────────────────

async def test_minecraft_afk_status_endpoint() -> None:
    mock = AsyncMock(return_value={"running": True, "enabled": True})
    with patch("app.routers.system.minecraft_afk", mock):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/system/minecraft-afk")
    assert resp.json() == {"running": True, "enabled": True}
    mock.assert_awaited_once_with("status")


async def test_minecraft_afk_control_rejects_unknown_action() -> None:
    mock = AsyncMock()
    with patch("app.routers.system.minecraft_afk", mock):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/system/minecraft-afk/reboot")
    assert resp.json() == {"error": "invalid_action"}
    mock.assert_not_awaited()


async def test_minecraft_afk_control_helper_unreachable() -> None:
    with patch("app.routers.system.minecraft_afk", AsyncMock(return_value=None)):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/system/minecraft-afk/stop")
    assert resp.json() == {"error": "host_helper_unreachable"}


async def test_minecraft_service_entry_states() -> None:
    from app.services.service_health import _minecraft_entry

    cases = [
        (None, "down", "확인 불가"),
        ({"enabled": False, "running": False}, "off", "꺼둠"),
        ({"enabled": True, "running": False}, "warn", "재실행 중"),
        ({"enabled": True, "running": True, "connected": False, "uptime_sec": 30}, "warn", "재접속 중"),
        ({"enabled": True, "running": True, "connected": True, "uptime_sec": 3 * 3600 + 120}, "up", "잠수 중"),
    ]
    for st, status, label in cases:
        with patch("app.services.host_helper.minecraft_afk", AsyncMock(return_value=st)):
            entry = await _minecraft_entry()
        assert (entry["status"], entry["label"]) == (status, label)
    assert "3시간 2분째" in entry["detail"]


async def test_minecraft_agent_tools() -> None:
    from app.tools import home

    with patch("app.tools.home.minecraft_afk", AsyncMock(return_value={"enabled": True})) as m:
        assert "시작" in await home.start_minecraft_afk(MagicMock())
        m.assert_awaited_with("start")
        assert "껐어" in await home.stop_minecraft_afk(MagicMock())
        m.assert_awaited_with("stop")
    with patch("app.tools.home.minecraft_afk", AsyncMock(return_value=None)):
        assert "실패" in await home.start_minecraft_afk(MagicMock())
    entry = {"label": "잠수 중", "detail": "띵타이쿤 접속 · 2시간 0분째"}
    with patch("app.tools.home._minecraft_entry", AsyncMock(return_value=entry)):
        assert await home.get_minecraft_afk_status(MagicMock()) == "잠수 중 — 띵타이쿤 접속 · 2시간 0분째"
