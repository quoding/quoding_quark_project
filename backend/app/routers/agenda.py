from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agenda import ScheduledEvent

router = APIRouter(prefix="/agenda", tags=["agenda"])


class EventCreate(BaseModel):
    title: str
    scheduled_at: datetime
    tag: str = "개인"


class EventUpdate(BaseModel):
    title: str | None = None
    scheduled_at: datetime | None = None
    tag: str | None = None
    done: bool | None = None


class EventOut(BaseModel):
    id: int
    title: str
    scheduled_at: datetime
    tag: str
    done: bool
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/events", response_model=list[EventOut])
async def list_events(
    date_filter: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ScheduledEvent]:
    stmt = select(ScheduledEvent).order_by(ScheduledEvent.scheduled_at)
    if date_filter is not None:
        day_start = datetime(date_filter.year, date_filter.month, date_filter.day, tzinfo=UTC)
        day_end = datetime(date_filter.year, date_filter.month, date_filter.day, 23, 59, 59, tzinfo=UTC)
        stmt = stmt.where(ScheduledEvent.scheduled_at >= day_start).where(
            ScheduledEvent.scheduled_at <= day_end
        )
    elif date_from is not None or date_to is not None:
        if date_from is not None:
            stmt = stmt.where(
                ScheduledEvent.scheduled_at >= datetime(date_from.year, date_from.month, date_from.day, tzinfo=UTC)
            )
        if date_to is not None:
            stmt = stmt.where(
                ScheduledEvent.scheduled_at <= datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=UTC)
            )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/events", response_model=EventOut, status_code=201)
async def create_event(
    body: EventCreate,
    db: AsyncSession = Depends(get_db),
) -> ScheduledEvent:
    ev = ScheduledEvent(title=body.title, scheduled_at=body.scheduled_at, tag=body.tag, done=False)
    db.add(ev)
    await db.flush()
    await db.refresh(ev)
    return ev


@router.patch("/events/{event_id}", response_model=EventOut)
async def update_event(
    event_id: int,
    body: EventUpdate,
    db: AsyncSession = Depends(get_db),
) -> ScheduledEvent:
    result = await db.execute(select(ScheduledEvent).where(ScheduledEvent.id == event_id))
    ev = result.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if body.title is not None:
        ev.title = body.title
    if body.scheduled_at is not None:
        ev.scheduled_at = body.scheduled_at
    if body.tag is not None:
        ev.tag = body.tag
    if body.done is not None:
        ev.done = body.done
    await db.flush()
    await db.refresh(ev)
    return ev


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(select(ScheduledEvent).where(ScheduledEvent.id == event_id))
    ev = result.scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(ev)
    return Response(status_code=204)
