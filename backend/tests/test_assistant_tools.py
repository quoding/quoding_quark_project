"""Tests for assistant agent tools (add_event, add_todo, web_search, etc.)."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.deps import QuarkDeps
from app.services.google_calendar import GoogleCalendarError
from app.services.mqtt_bridge import MqttBridge
from app.tools.assistant import (
    add_event,
    add_idea,
    add_todo,
    cancel_event,
    complete_todo,
    list_events,
    update_event,
    web_search,
)


def _make_ctx(db: Any = None) -> Any:
    bridge = MqttBridge()
    bridge.publish = AsyncMock()  # type: ignore[method-assign]
    deps = QuarkDeps(mqtt=bridge, db=db)
    return SimpleNamespace(deps=deps)


# ── no-DB fallbacks ───────────────────────────────────────────────────────────


async def test_add_todo_no_db() -> None:
    ctx = _make_ctx(db=None)
    result = await add_todo(ctx, "청소")
    assert "DB" in result


async def test_complete_todo_no_db() -> None:
    ctx = _make_ctx(db=None)
    result = await complete_todo(ctx, 1)
    assert "DB" in result


async def test_add_idea_no_db() -> None:
    ctx = _make_ctx(db=None)
    result = await add_idea(ctx, "새 아이디어")
    assert "DB" in result


# ── with mock DB ─────────────────────────────────────────────────────────────


async def test_add_event_creates_google_calendar_event() -> None:
    ctx = _make_ctx(db=None)
    fake_create = AsyncMock(return_value={"id": "evt1", "title": "데일리 회의", "start": "2026-06-10T09:00:00+09:00", "end": "2026-06-10T10:00:00+09:00", "all_day": False})
    with patch("app.services.google_calendar.create_event", fake_create):
        result = await add_event(ctx, "데일리 회의", "2026-06-10T09:00:00")
    assert "저장했어" in result
    assert "데일리 회의" in result
    fake_create.assert_awaited_once_with("데일리 회의", "2026-06-10T09:00:00", None)


async def test_add_event_reports_failure() -> None:
    ctx = _make_ctx(db=None)
    fake_create = AsyncMock(side_effect=GoogleCalendarError("연동 설정 없음"))
    with patch("app.services.google_calendar.create_event", fake_create):
        result = await add_event(ctx, "테스트", "2026-06-10T09:00:00")
    assert "실패" in result


async def test_add_todo_with_db() -> None:
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    ctx = _make_ctx(db=mock_db)
    result = await add_todo(ctx, "에어컨 필터 청소")
    assert "저장했어" in result


async def test_add_idea_with_db() -> None:
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    ctx = _make_ctx(db=mock_db)
    result = await add_idea(ctx, "LED 일출 알람", "하드웨어")
    assert "저장했어" in result


async def test_list_events_formats_id_and_time() -> None:
    ctx = _make_ctx(db=None)
    fake_list = AsyncMock(return_value=[
        {"id": "evt1", "title": "빌드 회의", "start": "2026-06-06T10:30:00+09:00", "end": "2026-06-06T11:30:00+09:00", "all_day": False},
        {"id": "evt2", "title": "워크숍", "start": "2026-06-06", "end": "2026-06-07", "all_day": True},
    ])
    with patch("app.services.google_calendar.list_events", fake_list):
        result = await list_events(ctx, "2026-06-06")
    assert "[evt1] 10:30 빌드 회의" in result
    assert "[evt2] 종일 워크숍" in result


async def test_list_events_empty() -> None:
    ctx = _make_ctx(db=None)
    with patch("app.services.google_calendar.list_events", AsyncMock(return_value=[])):
        result = await list_events(ctx, "2026-06-06")
    assert "일정 없음" in result


async def test_update_event_calls_service() -> None:
    ctx = _make_ctx(db=None)
    fake_update = AsyncMock(return_value={"id": "evt1", "title": "변경된 제목", "start": "2026-06-06T11:00:00+09:00", "end": "2026-06-06T12:00:00+09:00", "all_day": False})
    with patch("app.services.google_calendar.update_event", fake_update):
        result = await update_event(ctx, "evt1", title="변경된 제목")
    assert "수정했어" in result
    fake_update.assert_awaited_once_with("evt1", title="변경된 제목", start=None, end=None)


async def test_cancel_event_calls_service() -> None:
    ctx = _make_ctx(db=None)
    fake_delete = AsyncMock(return_value=None)
    with patch("app.services.google_calendar.delete_event", fake_delete):
        result = await cancel_event(ctx, "evt1")
    assert "취소했어" in result
    fake_delete.assert_awaited_once_with("evt1")


async def test_cancel_event_reports_failure() -> None:
    ctx = _make_ctx(db=None)
    fake_delete = AsyncMock(side_effect=GoogleCalendarError("실패"))
    with patch("app.services.google_calendar.delete_event", fake_delete):
        result = await cancel_event(ctx, "evt1")
    assert "실패" in result


async def test_complete_todo_with_db() -> None:
    from app.models.agenda import Todo

    todo = MagicMock(spec=Todo)
    todo.id = 1
    todo.text = "청소"
    todo.done = False

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = todo

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()

    ctx = _make_ctx(db=mock_db)
    result = await complete_todo(ctx, 1)
    assert "완료" in result
    assert todo.done is True


async def test_complete_todo_not_found() -> None:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    ctx = _make_ctx(db=mock_db)
    result = await complete_todo(ctx, 999)
    assert "없음" in result


# ── web_search ────────────────────────────────────────────────────────────────


async def test_web_search_returns_results() -> None:
    fake_results = [
        {"title": "ESP32 튜토리얼", "href": "https://example.com", "body": "ESP32 관련 내용"},
    ]
    ctx = _make_ctx()

    with patch("app.tools.assistant.DDGS") as mock_ddgs_cls:
        mock_ddgs_cls.return_value.text.return_value = fake_results
        result = await web_search(ctx, "ESP32 홈 자동화")

    assert "ESP32" in result


async def test_web_search_empty_results() -> None:
    ctx = _make_ctx()
    with patch("app.tools.assistant.DDGS") as mock_ddgs_cls:
        mock_ddgs_cls.return_value.text.return_value = []
        result = await web_search(ctx, "존재하지않는검색어123")
    assert result == "검색 결과 없음"


async def test_web_search_network_failure() -> None:
    ctx = _make_ctx()
    with patch("app.tools.assistant.DDGS") as mock_ddgs_cls:
        mock_ddgs_cls.return_value.text.side_effect = ConnectionError("timeout")
        result = await web_search(ctx, "테스트")
    assert result == "검색 결과 없음"
