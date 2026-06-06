"""Morning brief: content generation + Discord dispatch."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.quark_agent import quark_agent
from app.services.rag import create_morning_brief_content
from app.services.scheduler import _morning_brief, _send_discord_message


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


# ── create_morning_brief_content ─────────────────────────────────────────────


async def test_morning_brief_content_returns_string(mock_db: AsyncMock) -> None:
    mock_db.execute.return_value = MagicMock(
        scalars=lambda: MagicMock(all=lambda: [])
    )
    with quark_agent.override(model=TestModel(call_tools=[], custom_output_text="오늘도 좋은 하루야!")):
        content = await create_morning_brief_content(mock_db)
    assert isinstance(content, str) and content


# ── _send_discord_message ─────────────────────────────────────────────────────


async def test_send_discord_message_posts_to_api() -> None:
    mock_post = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    class _FakeClient:
        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *exc: object) -> bool:
            return False

        post = mock_post

    with patch("app.services.scheduler.httpx.AsyncClient", return_value=_FakeClient()):
        await _send_discord_message("123456", "tok", "오늘 날씨는 맑아!")

    mock_post.assert_awaited_once()
    call_kwargs: Any = mock_post.await_args.kwargs
    payload = call_kwargs.get("json") or {}
    assert "오늘" in payload.get("content", "")


# ── _morning_brief (scheduler) ───────────────────────────────────────────────


async def test_morning_brief_skipped_without_discord_config() -> None:
    with patch("app.services.scheduler.get_settings") as mock_cfg:
        mock_cfg.return_value.discord_channel_id = ""
        mock_cfg.return_value.discord_token = ""
        with patch("app.services.rag.create_morning_brief_content") as gen_mock:
            await _morning_brief()
    gen_mock.assert_not_called()


async def test_morning_brief_generates_and_sends() -> None:
    from typing import Any as _Any

    class _FakeSessionCtx:
        async def __aenter__(self) -> AsyncMock:
            db = AsyncMock()
            db.execute = AsyncMock(
                return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: []))
            )
            return db

        async def __aexit__(self, *exc: object) -> bool:
            return False

    mock_send = AsyncMock()
    mock_result = MagicMock()
    mock_result.output = "브리핑 텍스트"

    with (
        patch("app.services.scheduler.get_settings") as mock_cfg,
        patch("app.services.weather.get_current_weather", return_value={
            "temp": 25, "label": "맑음", "hi": 28, "lo": 20, "pm25": 10, "aqi_grade": "좋음",
        }),
        patch("app.core.database.AsyncSessionLocal", return_value=_FakeSessionCtx()),
        patch("app.agents.quark_agent.quark_agent") as mock_agent,
        patch("app.services.scheduler._send_discord_message", mock_send),
    ):
        mock_cfg.return_value.discord_channel_id = "999"
        mock_cfg.return_value.discord_token = "tok"
        mock_agent.run = AsyncMock(return_value=mock_result)
        await _morning_brief()

    mock_send.assert_awaited_once()
    args: _Any = mock_send.await_args
    assert "브리핑" in args[0][2]
