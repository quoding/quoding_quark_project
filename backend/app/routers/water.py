from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agenda import WaterLog

router = APIRouter(prefix="/water", tags=["water"])

GOAL_ML = 2000


class WaterOut(BaseModel):
    date: date
    total_ml: int
    goal_ml: int
    pct: int


class WaterLogOut(BaseModel):
    id: int
    date: date
    amount_ml: int
    created_at: datetime

    model_config = {"from_attributes": True}


async def _today_total(db: AsyncSession) -> int:
    today = date.today()
    result = await db.execute(select(WaterLog).where(WaterLog.date == today))
    logs = result.scalars().all()
    return sum(lg.amount_ml for lg in logs)


@router.get("/today", response_model=WaterOut)
async def get_today_water(db: AsyncSession = Depends(get_db)) -> WaterOut:
    total = await _today_total(db)
    return WaterOut(
        date=date.today(),
        total_ml=total,
        goal_ml=GOAL_ML,
        pct=min(100, round(total / GOAL_ML * 100)),
    )


@router.post("/today", response_model=WaterOut, status_code=201)
async def add_water(db: AsyncSession = Depends(get_db)) -> WaterOut:
    log = WaterLog(date=date.today(), amount_ml=250)
    db.add(log)
    await db.flush()
    await db.commit()
    total = await _today_total(db)
    return WaterOut(
        date=date.today(),
        total_ml=total,
        goal_ml=GOAL_ML,
        pct=min(100, round(total / GOAL_ML * 100)),
    )
