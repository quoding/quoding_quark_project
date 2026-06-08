from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException

from app.core.config import get_settings


async def verify_siri_token(authorization: Annotated[str | None, Header()] = None) -> None:
    """Require ``Authorization: Bearer <siri_api_key>`` for Siri-facing endpoints."""
    expected_key = get_settings().siri_api_key
    if not expected_key or authorization != f"Bearer {expected_key}":
        raise HTTPException(status_code=401, detail="unauthorized")
