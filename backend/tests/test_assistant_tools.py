"""Tests for assistant agent tools (add_event, add_todo, web_search, etc.)."""
from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.deps import QuarkDeps
from app.services.mqtt_bridge import MqttBridge
from app.tools.assistant import (
    add_event,
    add_idea,
    add_todo,
    complete_todo,
    list_events,
    web_search,
)


def _make_ctx(db: Any = None) -> Any:
    bridge = MqttBridge()
    bridge.publish = AsyncMock()  # type: ignore[method-assign]
    deps = QuarkDeps(mqtt=bridge, db=db)
    return SimpleNamespace(deps=deps)


# ── no-DB fallbacks ───────────────────────────────────────────────────────────


async def test_add_event_no_db() -> None:
    ctx = _make_ctx(db=None)
    result = await add_event(ctx, "미팅", "2026-06-10T14:00:00")
    assert "DB" in result


async def test_list_events_no_db() -> None:
    ctx = _make_ctx(db=None)
    result = await list_events(ctx)
    assert "DB" in result


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


async def test_add_event_with_db() -> None:
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    ctx = _make_ctx(db=mock_db)
    result = await add_event(ctx, "데일리 회의", "2026-06-10T09:00:00")
    assert "저장했어" in result
    mock_db.add.assert_called_once()


async def test_add_event_invalid_date() -> None:
    mock_db = AsyncMock()
    ctx = _make_ctx(db=mock_db)
    result = await add_event(ctx, "테스트", "not-a-date")
    assert "오류" in result


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


async def test_list_events_today(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.models.agenda import ScheduledEvent

    ev = MagicMock(spec=ScheduledEvent)
    ev.scheduled_at = datetime(2026, 6, 6, 10, 30, tzinfo=UTC)
    ev.title = "빌드 회의"
    ev.tag = "회의"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [ev]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    monkeypatch.setattr("app.tools.assistant.date", MagicMock(today=lambda: date(2026, 6, 6), fromisoformat=date.fromisoformat))
    ctx = _make_ctx(db=mock_db)
    result = await list_events(ctx)
    assert "빌드 회의" in result


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
