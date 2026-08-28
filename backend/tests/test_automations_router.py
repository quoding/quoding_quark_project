"""Automations router — seeding, toggle, and delete restricted to user macros."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.database import get_db
from app.main import app
from app.models.agenda import Automation


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
        self.deleted: list[Any] = []

    async def execute(self, *_: Any, **__: Any) -> _FakeResult:
        return _FakeResult(self._rows)

    async def commit(self) -> None:
        pass

    def add(self, _obj: Any) -> None:
        pass

    async def delete(self, obj: Any) -> None:
        self.deleted.append(obj)


def _override(session: _FakeSession) -> Any:
    async def _fake_db() -> AsyncGenerator[_FakeSession, None]:
        yield session

    return _fake_db


async def test_delete_system_automation_returns_409() -> None:
    auto = Automation(id=1, name="아침 브리핑", trigger_desc="매일 08:00", action_desc="...", icon="sun", kind="cron", slug="morning-brief")
    app.dependency_overrides[get_db] = _override(_FakeSession([auto]))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/automations/1")
        assert resp.status_code == 409
    finally:
        app.dependency_overrides.clear()


async def test_delete_macro_automation_succeeds() -> None:
    auto = Automation(id=2, name="취침 준비", trigger_desc="수동 실행 (매크로)", action_desc="...", icon="zap", kind="macro", slug=None)
    session = _FakeSession([auto])
    app.dependency_overrides[get_db] = _override(session)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/automations/2")
        assert resp.status_code == 204
        assert session.deleted == [auto]
    finally:
        app.dependency_overrides.clear()


async def test_list_automations_includes_kind() -> None:
    auto = Automation(
        id=3, name="습관 초기화", trigger_desc="매일 00:01", action_desc="...", icon="reset",
        kind="cron", slug="habit-daily-reset", enabled=True, run_count=0,
        created_at=datetime(2026, 8, 29, tzinfo=UTC),
    )
    app.dependency_overrides[get_db] = _override(_FakeSession([auto]))
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/automations")
        assert resp.status_code == 200
        assert resp.json()[0]["kind"] == "cron"
    finally:
        app.dependency_overrides.clear()
