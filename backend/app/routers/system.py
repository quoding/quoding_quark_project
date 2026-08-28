from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.docker_stats import get_docker_stats
from app.services.embeddings import is_embedding_enabled, set_embedding_enabled
from app.services.github_stats import get_github_stats
from app.services.host_helper import reboot_host, wake_on_lan
from app.services.market import get_market_data
from app.services.news import get_news
from app.services.notify import (
    is_discord_notify_enabled,
    is_push_notify_enabled,
    set_discord_notify_enabled,
    set_push_notify_enabled,
)
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


class EmbeddingToggleIn(BaseModel):
    enabled: bool


@router.get("/embedding-toggle")
async def get_embedding_toggle() -> dict[str, bool]:
    """RAG 임베딩(저장/검색) 활성화 여부 — 테스트 단계 토큰 절약용 토글."""
    return {"enabled": await is_embedding_enabled()}


@router.patch("/embedding-toggle")
async def patch_embedding_toggle(body: EmbeddingToggleIn) -> dict[str, bool]:
    await set_embedding_enabled(body.enabled)
    return {"enabled": body.enabled}


class NotifySettingsIn(BaseModel):
    discord_enabled: bool | None = None
    push_enabled: bool | None = None


@router.get("/notify-settings")
async def get_notify_settings() -> dict[str, bool]:
    return {
        "discord_enabled": await is_discord_notify_enabled(),
        "push_enabled": await is_push_notify_enabled(),
    }


@router.patch("/notify-settings")
async def patch_notify_settings(body: NotifySettingsIn) -> dict[str, bool]:
    if body.discord_enabled is not None:
        await set_discord_notify_enabled(body.discord_enabled)
    if body.push_enabled is not None:
        await set_push_notify_enabled(body.push_enabled)
    return {
        "discord_enabled": await is_discord_notify_enabled(),
        "push_enabled": await is_push_notify_enabled(),
    }


@router.post("/reboot")
async def reboot() -> dict[str, bool]:
    """미니PC를 재부팅한다 (호스트 헬퍼 경유)."""
    return {"ok": await reboot_host()}


@router.post("/wake-laptop")
async def wake_laptop_endpoint() -> dict[str, bool]:
    """Wake-on-LAN으로 노트북을 깨운다 (호스트 헬퍼 경유)."""
    mac = get_settings().laptop_mac
    if not mac:
        return {"ok": False}
    return {"ok": await wake_on_lan(mac)}
