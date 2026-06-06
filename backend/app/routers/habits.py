from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agenda import Habit

router = APIRouter(prefix="/habits", tags=["habits"])


class HabitCreate(BaseModel):
    name: str


class HabitOut(BaseModel):
    id: int
    name: str
    streak: int
    done_today: bool
    last_checked_date: date | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[HabitOut])
async def list_habits(db: AsyncSession = Depends(get_db)) -> list[Habit]:
    result = await db.execute(select(Habit).order_by(Habit.created_at))
    return list(result.scalars().all())


@router.post("", response_model=HabitOut, status_code=201)
async def create_habit(body: HabitCreate, db: AsyncSession = Depends(get_db)) -> Habit:
    habit = Habit(name=body.name, streak=0, done_today=False, last_checked_date=None)
    db.add(habit)
    await db.flush()
    await db.refresh(habit)
    return habit


@router.patch("/{habit_id}/check", response_model=HabitOut)
async def check_habit(habit_id: int, db: AsyncSession = Depends(get_db)) -> Habit:
    result = await db.execute(select(Habit).where(Habit.id == habit_id))
    habit = result.scalar_one_or_none()
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")

    today = date.today()
    if habit.done_today and habit.last_checked_date == today:
        # Already checked today — toggle off
        habit.done_today = False
        habit.streak = max(0, habit.streak - 1)
    else:
        # Check for streak continuity
        if habit.last_checked_date is not None:
            delta = (today - habit.last_checked_date).days
            if delta == 1:
                habit.streak += 1
            elif delta > 1:
                habit.streak = 1
            # delta == 0 means re-checking same day (already handled above)
        else:
            habit.streak = 1
        habit.done_today = True
        habit.last_checked_date = today

    await db.flush()
    await db.refresh(habit)
    return habit
