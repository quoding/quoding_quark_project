from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_siri_token
from app.core.database import get_db
from app.models.device import Device
from app.services.mqtt_bridge import mqtt_bridge

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/devices", tags=["devices"])


class CommandRequest(BaseModel):
    device_id: str
    metric: str
    value: Any


@router.post("/cmd", dependencies=[Depends(verify_siri_token)])
async def send_command(req: CommandRequest) -> dict[str, Any]:
    """Publish a device command to MQTT (quark/cmd/{device}/{metric})."""
    await mqtt_bridge.cmd(req.device_id, req.metric, req.value)
    return {"status": "sent", "device": req.device_id, "metric": req.metric}


@router.get("")
async def list_devices(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, list[dict[str, Any]]]:
    """Return the device registry from the DB (empty list when none registered)."""
    result = await db.execute(select(Device))
    devices = result.scalars().all()
    return {"devices": [d.as_dict() for d in devices]}
