from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agenda import Memo

router = APIRouter(prefix="/memo", tags=["memo"])


class MemoOut(BaseModel):
    id: int
    content: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoUpdate(BaseModel):
    content: str


async def _get_or_create(db: AsyncSession) -> Memo:
    result = await db.execute(select(Memo).limit(1))
    memo = result.scalar_one_or_none()
    if memo is None:
        memo = Memo(content="")
        db.add(memo)
        await db.flush()
    return memo


@router.get("", response_model=MemoOut)
async def get_memo(db: AsyncSession = Depends(get_db)) -> Memo:
    return await _get_or_create(db)


@router.put("", response_model=MemoOut)
async def update_memo(body: MemoUpdate, db: AsyncSession = Depends(get_db)) -> Memo:
    memo = await _get_or_create(db)
    memo.content = body.content
    await db.flush()
    await db.refresh(memo)
    return memo
