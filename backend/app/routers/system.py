from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.services.docker_stats import get_docker_stats
from app.services.github_stats import get_github_stats
from app.services.market import get_market_data
from app.services.news import get_news
from app.services.openai_usage import get_openai_usage
from app.services.service_health import get_service_health
from app.services.system_stats import get_system_stats
from app.services.transit import get_transit
from app.services.weather import get_current_weather, get_forecast

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/stats")
async def system_stats() -> dict[str, Any]:
    """Return live system stats (CPU, RAM, disk, temp, uptime)."""
    return get_system_stats()


@router.get("/weather")
async def current_weather() -> dict[str, Any]:
    """Return current weather + air quality from Open-Meteo."""
    return await get_current_weather()


@router.get("/forecast")
async def weather_forecast() -> dict[str, Any]:
    """Return 7-day hourly forecast + sunrise/sunset from Open-Meteo."""
    return await get_forecast()


@router.get("/docker")
async def docker_stats() -> list[dict[str, Any]]:
    """Return Docker container stats (10s cache)."""
    return get_docker_stats()


@router.get("/services")
async def service_health() -> list[dict[str, Any]]:
    """Return internal service health (5s cache)."""
    return await get_service_health()


@router.get("/market")
async def market_data() -> dict[str, Any]:
    """Return crypto + FX market data (10min cache)."""
    return await get_market_data()


@router.get("/news")
async def news_feed() -> list[dict[str, Any]]:
    """Return latest RSS news (30min cache)."""
    return get_news()


@router.get("/github")
async def github_stats() -> dict[str, Any]:
    """Return GitHub contribution stats (1h cache)."""
    return await get_github_stats()


@router.get("/transit")
async def transit_data() -> list[dict[str, Any]]:
    """Return real-time transit arrivals."""
    return await get_transit()


@router.get("/openai-usage")
async def openai_usage() -> dict[str, Any]:
    """Return today's OpenAI API usage (daily cache)."""
    return await get_openai_usage()
