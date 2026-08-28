from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.push import PushSubscription
from app.services.push import send_test

router = APIRouter(prefix="/push", tags=["push"])


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class SubscribeRequest(BaseModel):
    endpoint: str
    keys: PushKeys


@router.get("/public-key")
async def public_key() -> dict[str, str]:
    return {"key": get_settings().vapid_public_key}


@router.post("/subscribe", status_code=204, response_class=Response)
async def subscribe(body: SubscribeRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> Response:
    stmt = (
        insert(PushSubscription)
        .values(endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth)
        .on_conflict_do_update(
            index_elements=[PushSubscription.endpoint],
            set_={"p256dh": body.keys.p256dh, "auth": body.keys.auth},
        )
    )
    await db.execute(stmt)
    await db.commit()
    return Response(status_code=204)


@router.post("/test")
async def test(db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, int]:
    return await send_test(db)


@router.get("/status")
async def status(db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, int]:
    result = await db.execute(select(PushSubscription))
    return {"subscriptions": len(list(result.scalars().all()))}
