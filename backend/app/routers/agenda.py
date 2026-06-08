from __future__ import annotations

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.services import google_calendar

router = APIRouter(prefix="/agenda", tags=["agenda"])

_TIMEZONE_SUFFIX = "+09:00"


class EventCreate(BaseModel):
    title: str
    scheduled_at: datetime
    end_at: datetime | None = None


class EventUpdate(BaseModel):
    title: str | None = None
    scheduled_at: datetime | None = None
    end_at: datetime | None = None


class EventOut(BaseModel):
    id: str
    title: str
    scheduled_at: str
    end_at: str | None
    all_day: bool


def _day_range(d: date) -> tuple[str, str]:
    start = datetime.combine(d, time.min).isoformat() + _TIMEZONE_SUFFIX
    end = datetime.combine(d, time.max.replace(microsecond=0)).isoformat() + _TIMEZONE_SUFFIX
    return start, end


def _to_event_out(ev: dict[str, object]) -> EventOut:
    return EventOut(
        id=str(ev["id"]),
        title=str(ev["title"]),
        scheduled_at=str(ev["start"]),
        end_at=ev["end"] if ev["end"] is None else str(ev["end"]),
        all_day=bool(ev["all_day"]),
    )


@router.get("/events", response_model=list[EventOut])
async def list_events(
    date_filter: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[EventOut]:
    if date_filter is not None:
        time_min, time_max = _day_range(date_filter)
    elif date_from is not None or date_to is not None:
        start_date = date_from or date.today()
        end_date = date_to or start_date
        time_min, _ = _day_range(start_date)
        _, time_max = _day_range(end_date)
    else:
        today = date.today()
        time_min, _ = _day_range(today)
        _, time_max = _day_range(today + timedelta(days=30))

    events = await google_calendar.list_events(time_min, time_max)
    return [_to_event_out(ev) for ev in events]


@router.post("/events", response_model=EventOut, status_code=201)
async def create_event(body: EventCreate) -> EventOut:
    try:
        ev = await google_calendar.create_event(
            body.title,
            body.scheduled_at.isoformat(),
            body.end_at.isoformat() if body.end_at else None,
        )
    except google_calendar.GoogleCalendarError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    return _to_event_out(ev)


@router.patch("/events/{event_id}", response_model=EventOut)
async def update_event(event_id: str, body: EventUpdate) -> EventOut:
    try:
        ev = await google_calendar.update_event(
            event_id,
            title=body.title,
            start=body.scheduled_at.isoformat() if body.scheduled_at else None,
            end=body.end_at.isoformat() if body.end_at else None,
        )
    except google_calendar.GoogleCalendarError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return _to_event_out(ev)


@router.delete("/events/{event_id}")
async def delete_event(event_id: str) -> Response:
    try:
        await google_calendar.delete_event(event_id)
    except google_calendar.GoogleCalendarError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    return Response(status_code=204)
