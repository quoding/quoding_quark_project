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
