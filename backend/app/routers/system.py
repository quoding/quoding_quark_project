from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.services.system_stats import get_system_stats
from app.services.weather import get_current_weather

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/stats")
async def system_stats() -> dict[str, Any]:
    """Return live system stats (CPU, RAM, disk, temp, uptime)."""
    return get_system_stats()


@router.get("/weather")
async def current_weather() -> dict[str, Any]:
    """Return current weather + air quality from Open-Meteo."""
    return await get_current_weather()
