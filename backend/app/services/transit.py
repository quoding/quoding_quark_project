"""Transit real-time data — returns empty list when API key not configured."""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


async def get_transit() -> list[dict[str, Any]]:
    """Return transit arrivals. Returns [] when TRANSIT_API_KEY not set."""
    api_key = os.environ.get("TRANSIT_API_KEY", "")
    if not api_key:
        return []

    # Placeholder: implement with Seoul bus/subway API once key is provided
    return []
