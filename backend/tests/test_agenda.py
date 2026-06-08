"""Tests for agenda, todos, habits, and ideas CRUD routers."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx

from app.core.database import get_db
from app.main import app
from app.services.google_calendar import GoogleCalendarError

# ── DB stub helpers ───────────────────────────────────────────────────────────


class _FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeResult:
        return self

    def all(self) -> list[Any]:
        return self._rows

    def scalar_one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None


class _FakeSession:
    def __init__(self, rows: list[Any] | None = None) -> None:
        self._rows = rows or []
        self.added: list[Any] = []
        self.deleted: list[Any] = []

    async def execute(self, *_: Any, **__: Any) -> _FakeResult:
        return _FakeResult(self._rows)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def delete(self, obj: Any) -> None:
        self.deleted.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if not hasattr(obj, "id") or obj.id is None:
                obj.id = 1

    async def refresh(self, obj: Any) -> None:
        if not hasattr(obj, "created_at") or obj.created_at is None:
            obj.created_at = datetime(2026, 6, 6, 8, 0, tzinfo=UTC)


def _override(session: _FakeSession) -> Any:
    async def _fake_db() -> AsyncGenerator[_FakeSession, None]:
        yield session

    return _fake_db


# ── /api/agenda/events (Google Calendar 프록시 — google_calendar 서비스 모킹) ──────


async def test_list_events_empty() -> None:
    with patch("app.services.google_calendar.list_events", AsyncMock(return_value=[])):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/agenda/events")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_events_returns_normalized_events() -> None:
    fake_list = AsyncMock(return_value=[
        {"id": "evt1", "title": "회의", "start": "2026-06-10T14:00:00+09:00", "end": "2026-06-10T15:00:00+09:00", "all_day": False},
    ])
    with patch("app.services.google_calendar.list_events", fake_list):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/agenda/events?date_filter=2026-06-10")
    assert resp.status_code == 200
    assert resp.json() == [
        {"id": "evt1", "title": "회의", "scheduled_at": "2026-06-10T14:00:00+09:00", "end_at": "2026-06-10T15:00:00+09:00", "all_day": False},
    ]


async def test_create_event() -> None:
    fake_create = AsyncMock(return_value={"id": "evt1", "title": "회의", "start": "2026-06-10T14:00:00+09:00", "end": "2026-06-10T15:00:00+09:00", "all_day": False})
    with patch("app.services.google_calendar.create_event", fake_create):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/agenda/events",
                json={"title": "회의", "scheduled_at": "2026-06-10T14:00:00+09:00"},
            )
    assert resp.status_code == 201
    assert resp.json()["title"] == "회의"


async def test_create_event_reports_upstream_failure() -> None:
    fake_create = AsyncMock(side_effect=GoogleCalendarError("연동 설정 없음"))
    with patch("app.services.google_calendar.create_event", fake_create):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/api/agenda/events",
                json={"title": "회의", "scheduled_at": "2026-06-10T14:00:00+09:00"},
            )
    assert resp.status_code == 502


async def test_update_event_not_found() -> None:
    fake_update = AsyncMock(side_effect=GoogleCalendarError("not found"))
    with patch("app.services.google_calendar.update_event", fake_update):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.patch("/api/agenda/events/999", json={"title": "변경"})
    assert resp.status_code == 404


async def test_delete_event_not_found() -> None:
    fake_delete = AsyncMock(side_effect=GoogleCalendarError("not found"))
    with patch("app.services.google_calendar.delete_event", fake_delete):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/agenda/events/999")
    assert resp.status_code == 404


async def test_delete_event_succeeds() -> None:
    fake_delete = AsyncMock(return_value=None)
    with patch("app.services.google_calendar.delete_event", fake_delete):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/agenda/events/evt1")
    assert resp.status_code == 204
    fake_delete.assert_awaited_once_with("evt1")


# ── /api/todos ────────────────────────────────────────────────────────────────


async def test_list_todos_empty() -> None:
    app.dependency_overrides[get_db] = _override(_FakeSession([]))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/todos")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.clear()


async def test_create_todo() -> None:
    from app.models.agenda import Todo

    todo = Todo(
        id=1,
        text="에어컨 필터 청소",
        done=False,
        created_at=datetime(2026, 6, 6, 8, 0, tzinfo=UTC),
    )
    app.dependency_overrides[get_db] = _override(_FakeSession([todo]))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/todos", json={"text": "에어컨 필터 청소"})
        assert resp.status_code == 201
        assert resp.json()["text"] == "에어컨 필터 청소"
    finally:
        app.dependency_overrides.clear()


async def test_toggle_todo() -> None:
    from app.models.agenda import Todo

    todo = Todo(
        id=1,
        text="테스트",
        done=False,
        created_at=datetime(2026, 6, 6, 8, 0, tzinfo=UTC),
    )
    app.dependency_overrides[get_db] = _override(_FakeSession([todo]))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.patch("/api/todos/1")
        assert resp.status_code == 200
        # done should be toggled
        assert resp.json()["done"] is True
    finally:
        app.dependency_overrides.clear()


async def test_toggle_todo_not_found() -> None:
    app.dependency_overrides[get_db] = _override(_FakeSession([]))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.patch("/api/todos/999")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ── /api/habits ───────────────────────────────────────────────────────────────


async def test_list_habits_empty() -> None:
    app.dependency_overrides[get_db] = _override(_FakeSession([]))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/habits")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.clear()


async def test_create_habit() -> None:
    from app.models.agenda import Habit

    habit = Habit(
        id=1,
        name="아침 스트레칭",
        streak=0,
        done_today=False,
        last_checked_date=None,
        created_at=datetime(2026, 6, 6, 8, 0, tzinfo=UTC),
    )
    app.dependency_overrides[get_db] = _override(_FakeSession([habit]))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/habits", json={"name": "아침 스트레칭"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "아침 스트레칭"
    finally:
        app.dependency_overrides.clear()


async def test_check_habit_new() -> None:
    from app.models.agenda import Habit

    habit = Habit(
        id=1,
        name="물 마시기",
        streak=0,
        done_today=False,
        last_checked_date=None,
        created_at=datetime(2026, 6, 6, 8, 0, tzinfo=UTC),
    )
    app.dependency_overrides[get_db] = _override(_FakeSession([habit]))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.patch("/api/habits/1/check")
        assert resp.status_code == 200
        data = resp.json()
        assert data["done_today"] is True
        assert data["streak"] == 1
    finally:
        app.dependency_overrides.clear()


# ── /api/ideas ────────────────────────────────────────────────────────────────


async def test_list_ideas_empty() -> None:
    app.dependency_overrides[get_db] = _override(_FakeSession([]))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/ideas")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.clear()


async def test_create_idea() -> None:
    from app.models.agenda import Idea

    idea = Idea(
        id=1,
        text="LED 스트립 일출 알람",
        tag="하드웨어",
        created_at=datetime(2026, 6, 6, 8, 0, tzinfo=UTC),
    )
    app.dependency_overrides[get_db] = _override(_FakeSession([idea]))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/ideas", json={"text": "LED 스트립 일출 알람", "tag": "하드웨어"})
        assert resp.status_code == 201
        assert resp.json()["text"] == "LED 스트립 일출 알람"
    finally:
        app.dependency_overrides.clear()


# ── route existence ───────────────────────────────────────────────────────────


def test_new_routes_registered() -> None:
    paths = {getattr(r, "path", "") for r in app.routes}
    for required in (
        "/api/agenda/events",
        "/api/todos",
        "/api/habits",
        "/api/ideas",
        "/api/system/stats",
        "/api/system/weather",
    ):
        assert required in paths, f"missing route {required}"
