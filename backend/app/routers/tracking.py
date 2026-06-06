"""Mood, Sleep, Caffeine, D-Day, and Alert CRUD endpoints."""
from __future__ import annotations

import datetime as _dt
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agenda import Alert, CaffeineLog, DdayItem, MoodLog, SleepLog

router = APIRouter(tags=["tracking"])

# ─── Mood ─────────────────────────────────────────────────────────────────────

class MoodIn(BaseModel):
    score: int  # 1-5
    note: str | None = None


class MoodOut(BaseModel):
    id: int
    date: date
    score: int
    note: str | None

    model_config = {"from_attributes": True}


@router.get("/mood", response_model=MoodOut | None)
async def get_today_mood(db: AsyncSession = Depends(get_db)) -> MoodLog | None:
    today = date.today()
    res = await db.execute(
        select(MoodLog).where(MoodLog.date == today).order_by(MoodLog.id.desc()).limit(1)
    )
    return res.scalar_one_or_none()


@router.post("/mood", response_model=MoodOut, status_code=201)
async def log_mood(body: MoodIn, db: AsyncSession = Depends(get_db)) -> MoodLog:
    if not 1 <= body.score <= 5:
        raise HTTPException(400, "score must be 1-5")
    entry = MoodLog(date=date.today(), score=body.score, note=body.note)
    db.add(entry)
    await db.flush()
    await db.commit()
    await db.refresh(entry)
    return entry


# ─── Sleep ────────────────────────────────────────────────────────────────────

class SleepIn(BaseModel):
    hours: float
    quality: int  # 1-5


class SleepOut(BaseModel):
    id: int
    date: date
    hours: float
    quality: int

    model_config = {"from_attributes": True}


@router.get("/sleep", response_model=SleepOut | None)
async def get_today_sleep(db: AsyncSession = Depends(get_db)) -> SleepLog | None:
    today = date.today()
    res = await db.execute(
        select(SleepLog).where(SleepLog.date == today).order_by(SleepLog.id.desc()).limit(1)
    )
    return res.scalar_one_or_none()


@router.post("/sleep", response_model=SleepOut, status_code=201)
async def log_sleep(body: SleepIn, db: AsyncSession = Depends(get_db)) -> SleepLog:
    if not 1 <= body.quality <= 5:
        raise HTTPException(400, "quality must be 1-5")
    entry = SleepLog(date=date.today(), hours=body.hours, quality=body.quality)
    db.add(entry)
    await db.flush()
    await db.commit()
    await db.refresh(entry)
    return entry


# ─── Caffeine ─────────────────────────────────────────────────────────────────

class CaffeineOut(BaseModel):
    date: date
    cups_today: int
    mg_today: int


@router.get("/caffeine", response_model=CaffeineOut)
async def get_today_caffeine(db: AsyncSession = Depends(get_db)) -> CaffeineOut:
    today = date.today()
    res = await db.execute(
        select(func.sum(CaffeineLog.amount_mg)).where(CaffeineLog.date == today)
    )
    total_mg: int = res.scalar_one() or 0
    cups = total_mg // 100
    return CaffeineOut(date=today, cups_today=cups, mg_today=total_mg)


@router.post("/caffeine", response_model=CaffeineOut, status_code=201)
async def add_caffeine_cup(db: AsyncSession = Depends(get_db)) -> CaffeineOut:
    today = date.today()
    entry = CaffeineLog(date=today, amount_mg=100)
    db.add(entry)
    await db.flush()
    await db.commit()
    res = await db.execute(
        select(func.sum(CaffeineLog.amount_mg)).where(CaffeineLog.date == today)
    )
    total_mg: int = res.scalar_one() or 0
    return CaffeineOut(date=today, cups_today=total_mg // 100, mg_today=total_mg)


# ─── D-Day ────────────────────────────────────────────────────────────────────

class DdayIn(BaseModel):
    label: str
    target_date: date


class DdayOut(BaseModel):
    id: int
    label: str
    target_date: date
    days: int

    model_config = {"from_attributes": True}


def _days_left(target: date) -> int:
    return (target - date.today()).days


@router.get("/dday", response_model=list[DdayOut])
async def list_ddays(db: AsyncSession = Depends(get_db)) -> list[DdayOut]:
    res = await db.execute(select(DdayItem).order_by(DdayItem.target_date))
    items = res.scalars().all()
    return [DdayOut(id=it.id, label=it.label, target_date=it.target_date, days=_days_left(it.target_date)) for it in items]


@router.post("/dday", response_model=DdayOut, status_code=201)
async def create_dday(body: DdayIn, db: AsyncSession = Depends(get_db)) -> DdayOut:
    item = DdayItem(label=body.label, target_date=body.target_date)
    db.add(item)
    await db.flush()
    await db.commit()
    await db.refresh(item)
    return DdayOut(id=item.id, label=item.label, target_date=item.target_date, days=_days_left(item.target_date))


@router.delete("/dday/{item_id}", status_code=204, response_class=Response)
async def delete_dday(item_id: int, db: AsyncSession = Depends(get_db)) -> Response:
    res = await db.execute(select(DdayItem).where(DdayItem.id == item_id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "not found")
    await db.delete(item)
    await db.commit()
    return Response(status_code=204)


# ─── Alerts ───────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: int
    title: str
    body: str
    urgent: bool
    read: bool
    created_at: _dt.datetime

    model_config = {"from_attributes": True}


@router.get("/alerts", response_model=list[AlertOut])
async def list_alerts(db: AsyncSession = Depends(get_db)) -> list[Alert]:
    res = await db.execute(select(Alert).order_by(Alert.created_at.desc()).limit(50))
    return list(res.scalars().all())


@router.patch("/alerts/{alert_id}/read", response_model=AlertOut)
async def mark_read(alert_id: int, db: AsyncSession = Depends(get_db)) -> Alert:
    res = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "not found")
    alert.read = True
    await db.commit()
    await db.refresh(alert)
    return alert


@router.delete("/alerts/{alert_id}", status_code=204, response_class=Response)
async def delete_alert(alert_id: int, db: AsyncSession = Depends(get_db)) -> Response:
    res = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "not found")
    await db.delete(alert)
    await db.commit()
    return Response(status_code=204)
