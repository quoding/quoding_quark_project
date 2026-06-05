from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.mqtt_bridge import mqtt_bridge

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/devices", tags=["devices"])


class CommandRequest(BaseModel):
    device_id: str
    metric: str
    value: Any


@router.post("/cmd")
async def send_command(req: CommandRequest) -> dict:
    await mqtt_bridge.cmd(req.device_id, req.metric, req.value)
    return {"status": "sent", "device": req.device_id, "metric": req.metric}


@router.get("/")
async def list_devices() -> dict:
    # TODO: fetch from DB device registry
    return {"devices": []}
