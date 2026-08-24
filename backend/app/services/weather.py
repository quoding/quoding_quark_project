from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_RETRY_ATTEMPTS = 3  # 최초 시도 + 2회 재시도
_RETRY_BASE_DELAY = 1.0  # 초, 시도마다 2배씩 증가


async def _get_with_retry(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> httpx.Response:
    """일시적 네트워크 오류/서버 오류만 짧게 재시도. 429는 서버 지시를 우선 따르고,
    4xx(요청 자체 문제)는 재시도해도 소용없으니 바로 실패시킨다 — API를 과호출해서
    차단당하는 상황을 피하기 위함."""
    delay = _RETRY_BASE_DELAY
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        last_attempt = attempt == _RETRY_ATTEMPTS
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 429 and not last_attempt:
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else delay * 2
                logger.warning("Weather API rate-limited, backing off %.1fs", wait)
                await asyncio.sleep(wait)
                delay *= 2
                continue
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as exc:
            if 500 <= exc.response.status_code < 600 and not last_attempt:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise
        except (httpx.TimeoutException, httpx.TransportError):
            if not last_attempt:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError("unreachable")  # pragma: no cover

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

_city_cache: dict[str, Any] = {}


async def _get_city_name() -> str:
    """좌표 → 지역명 (OpenStreetMap Nominatim reverse geocoding, 키 불필요).

    좌표는 설정값이라 자주 바뀌지 않으므로 프로세스 생애주기 동안 캐시한다.
    """
    settings = get_settings()
    cache_key = f"{settings.weather_lat},{settings.weather_lon}"
    if _city_cache.get("key") == cache_key:
        return _city_cache["name"]

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": settings.weather_lat,
                    "lon": settings.weather_lon,
                    "format": "jsonv2",
                    "accept-language": "ko",
                    "zoom": 14,
                },
                headers={"User-Agent": "quark-personal-assistant/1.0"},
            )
            resp.raise_for_status()
            address: dict[str, Any] = resp.json().get("address", {})

        name = (
            address.get("city")
            or address.get("town")
            or address.get("county")
            or address.get("state")
            or "알 수 없음"
        )
        _city_cache["key"] = cache_key
        _city_cache["name"] = name
        return name
    except Exception as exc:
        logger.warning("Reverse geocoding failed: %s", exc)
        return "알 수 없음"


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
            weather_resp = await _get_with_retry(
                client,
                "https://api.open-meteo.com/v1/forecast",
                {
                    "latitude": settings.weather_lat,
                    "longitude": settings.weather_lon,
                    "current": "temperature_2m,weather_code",
                    "daily": "temperature_2m_max,temperature_2m_min",
                    "timezone": "Asia/Seoul",
                    "forecast_days": 1,
                },
            )
            wd: dict[str, Any] = weather_resp.json()

        async with httpx.AsyncClient(timeout=8.0) as client:
            aqi_resp = await _get_with_retry(
                client,
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                {
                    "latitude": settings.weather_lat,
                    "longitude": settings.weather_lon,
                    "current": "pm2_5",
                    "timezone": "Asia/Seoul",
                },
            )
            aqd: dict[str, Any] = aqi_resp.json()

        temp: float = wd["current"]["temperature_2m"]
        code: int = wd["current"]["weather_code"]
        hi: float = wd["daily"]["temperature_2m_max"][0]
        lo: float = wd["daily"]["temperature_2m_min"][0]
        pm25: float = aqd["current"]["pm2_5"]
        city = await _get_city_name()

        return {
            "temp": round(temp, 1),
            "label": _wmo_label(code),
            "hi": round(hi, 1),
            "lo": round(lo, 1),
            "pm25": round(pm25, 1),
            "aqi_grade": _pm25_grade(pm25),
            "city": city,
        }
    except Exception as exc:
        logger.warning("Weather fetch failed: %s", exc)
        return {"error": str(exc)}
