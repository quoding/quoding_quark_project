"""Market data: crypto (CoinGecko) + FX (ExchangeRate-API) with 10-min cache."""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {}
_CACHE_TTL = 600.0  # 10 minutes


async def get_market_data() -> dict[str, Any]:
    """Return BTC/ETH KRW prices and USD/KRW exchange rate (10min cache)."""
    if _cache.get("ts") and time.monotonic() - _cache["ts"] < _CACHE_TTL:
        return _cache["data"]

    result: dict[str, Any] = {"crypto": [], "fx": []}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": "bitcoin,ethereum",
                    "vs_currencies": "krw",
                    "include_24hr_change": "true",
                },
            )
            resp.raise_for_status()
            cd: dict[str, Any] = resp.json()

        btc = cd.get("bitcoin", {})
        eth = cd.get("ethereum", {})
        result["crypto"] = [
            {
                "sym": "BTC",
                "name": "비트코인",
                "price": btc.get("krw", 0),
                "chg": round(btc.get("krw_24h_change", 0), 2),
            },
            {
                "sym": "ETH",
                "name": "이더리움",
                "price": eth.get("krw", 0),
                "chg": round(eth.get("krw_24h_change", 0), 2),
            },
        ]
    except Exception as exc:
        logger.warning("CoinGecko fetch failed: %s", exc)

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get("https://open.er-api.com/v6/latest/USD")
            resp.raise_for_status()
            fd: dict[str, Any] = resp.json()

        rates = fd.get("rates", {})
        krw_rate = rates.get("KRW", 0)
        jpy_rate = rates.get("JPY", 0)
        krw_per_100jpy = round((krw_rate / jpy_rate) * 100, 0) if jpy_rate else 0

        result["fx"] = [
            {"sym": "USD", "name": "달러", "price": round(krw_rate, 0), "chg": 0.0},
            {"sym": "JPY", "name": "엔화(100)", "price": krw_per_100jpy, "chg": 0.0},
        ]
    except Exception as exc:
        logger.warning("ExchangeRate fetch failed: %s", exc)

    _cache["data"] = result
    _cache["ts"] = time.monotonic()
    return result
