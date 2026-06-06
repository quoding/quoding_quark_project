from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_WMO_LABEL: dict[int, str] = {
    0: "맑음",
    1: "대체로 맑음",
    2: "구름 조금",
    3: "흐림",
    45: "안개",
    48: "안개",
    51: "이슬비",
    53: "이슬비",
    55: "이슬비",
    61: "가벼운 비",
    63: "비",
    65: "강한 비",
    71: "가벼운 눈",
    73: "눈",
    75: "강한 눈",
    80: "소나기",
    81: "소나기",
    82: "강한 소나기",
    95: "뇌우",
    96: "뇌우+우박",
    99: "뇌우+우박",
}


def _wmo_label(code: int) -> str:
    return _WMO_LABEL.get(code, "알 수 없음")


def _pm25_grade(pm25: float) -> str:
    if pm25 <= 15:
        return "좋음"
    if pm25 <= 35:
        return "보통"
    if pm25 <= 75:
        return "나쁨"
    return "매우나쁨"


_WMO_ICO: dict[int, str] = {
    0: "sun",
    1: "sun",
    2: "cloud",
    3: "cloud",
    45: "cloud",
    48: "cloud",
    51: "rain",
    53: "rain",
    55: "rain",
    61: "rain",
    63: "rain",
    65: "rain",
    71: "snow",
    73: "snow",
    75: "snow",
    80: "rain",
    81: "rain",
    82: "rain",
    95: "storm",
    96: "storm",
    99: "storm",
}

_DAY_KO = ["일", "월", "화", "수", "목", "금", "토"]


def _wmo_ico(code: int) -> str:
    return _WMO_ICO.get(code, "cloud")


_forecast_cache: dict[str, Any] = {}
_FORECAST_TTL = 600.0  # 10 minutes


async def get_forecast() -> dict[str, Any]:
    """Fetch 7-day daily forecast + sunrise/sunset from Open-Meteo."""
    import time

    if _forecast_cache.get("ts") and time.monotonic() - _forecast_cache["ts"] < _FORECAST_TTL:
        return _forecast_cache["data"]

    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": settings.weather_lat,
                    "longitude": settings.weather_lon,
                    "daily": (
                        "temperature_2m_max,temperature_2m_min,"
                        "precipitation_probability_max,weather_code,"
                        "sunrise,sunset"
                    ),
                    "timezone": "Asia/Seoul",
                    "forecast_days": 7,
                },
            )
            resp.raise_for_status()
            wd: dict[str, Any] = resp.json()

        daily = wd["daily"]
        days: list[dict[str, Any]] = []
        for i in range(7):
            date_str: str = daily["time"][i]
            import datetime as _dt

            d = _dt.date.fromisoformat(date_str)
            days.append(
                {
                    "d": _DAY_KO[d.weekday()] if i > 0 else "오늘",
                    "ico": _wmo_ico(daily["weather_code"][i]),
                    "pop": daily["precipitation_probability_max"][i] or 0,
                    "hi": round(daily["temperature_2m_max"][i], 1),
                    "lo": round(daily["temperature_2m_min"][i], 1),
                }
            )

        sunrise_raw: str = daily["sunrise"][0]
        sunset_raw: str = daily["sunset"][0]
        sunrise = sunrise_raw[11:16] if len(sunrise_raw) >= 16 else sunrise_raw
        sunset = sunset_raw[11:16] if len(sunset_raw) >= 16 else sunset_raw

        import datetime as _dt2

        def _to_min(t: str) -> int:
            h, m = map(int, t.split(":"))
            return h * 60 + m

        rise_min = _to_min(sunrise)
        set_min = _to_min(sunset)
        day_total = set_min - rise_min
        day_len = f"{day_total // 60}h {day_total % 60}m"

        result: dict[str, Any] = {
            "forecast": days,
            "sunrise": sunrise,
            "sunset": sunset,
            "day_len": day_len,
        }
        _forecast_cache["data"] = result
        _forecast_cache["ts"] = time.monotonic()
        return result
    except Exception as exc:
        logger.warning("Forecast fetch failed: %s", exc)
        return {"error": str(exc)}


async def get_current_weather() -> dict[str, Any]:
    """Fetch current weather + air quality from Open-Meteo (no API key required).

    Returns a dict with keys: temp, label, hi, lo, pm25, aqi_grade.
    On failure returns {"error": "<message>"}.
    """
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            weather_resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": settings.weather_lat,
                    "longitude": settings.weather_lon,
                    "current": "temperature_2m,weather_code",
                    "daily": "temperature_2m_max,temperature_2m_min",
                    "timezone": "Asia/Seoul",
                    "forecast_days": 1,
                },
            )
            weather_resp.raise_for_status()
            wd: dict[str, Any] = weather_resp.json()

        async with httpx.AsyncClient(timeout=8.0) as client:
            aqi_resp = await client.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={
                    "latitude": settings.weather_lat,
                    "longitude": settings.weather_lon,
                    "current": "pm2_5",
                    "timezone": "Asia/Seoul",
                },
            )
            aqi_resp.raise_for_status()
            aqd: dict[str, Any] = aqi_resp.json()

        temp: float = wd["current"]["temperature_2m"]
        code: int = wd["current"]["weather_code"]
        hi: float = wd["daily"]["temperature_2m_max"][0]
        lo: float = wd["daily"]["temperature_2m_min"][0]
        pm25: float = aqd["current"]["pm2_5"]

        return {
            "temp": round(temp, 1),
            "label": _wmo_label(code),
            "hi": round(hi, 1),
            "lo": round(lo, 1),
            "pm25": round(pm25, 1),
            "aqi_grade": _pm25_grade(pm25),
        }
    except Exception as exc:
        logger.warning("Weather fetch failed: %s", exc)
        return {"error": str(exc)}
