"""Tests for system stats and weather endpoints."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

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

    call_count = 0

    async def mock_get(*_: Any, **__: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        return mock_weather_resp if call_count == 1 else mock_aqi_resp

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
