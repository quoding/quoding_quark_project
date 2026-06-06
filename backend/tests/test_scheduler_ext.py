"""Tests for enhanced scheduler jobs: weekly_review and commit_reminder."""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.scheduler import _commit_reminder, _weekly_review

# ── _weekly_review ────────────────────────────────────────────────────────────


async def test_weekly_review_skipped_no_discord() -> None:
    with patch("app.services.scheduler.get_settings") as mock_cfg:
        mock_cfg.return_value.discord_channel_id = ""
        mock_cfg.return_value.discord_token = ""
        mock_cfg.return_value.github_username = ""
        with patch("app.services.scheduler._send_discord_message") as send_mock:
            await _weekly_review()
    send_mock.assert_not_called()


async def test_weekly_review_generates_and_sends() -> None:
    mock_send = AsyncMock()

    class _FakeSessionCtx:
        async def __aenter__(self) -> AsyncMock:
            db = AsyncMock()
            db.execute = AsyncMock(
                return_value=MagicMock(
                    scalars=lambda: MagicMock(all=lambda: [])
                )
            )
            return db

        async def __aexit__(self, *_: Any) -> bool:
            return False

    with (
        patch("app.services.scheduler.get_settings") as mock_cfg,
        patch("app.core.database.AsyncSessionLocal", return_value=_FakeSessionCtx()),
        patch("app.services.scheduler._send_discord_message", mock_send),
        patch("app.agents.quark_agent.quark_agent") as mock_agent,
    ):
        mock_cfg.return_value.discord_channel_id = "123"
        mock_cfg.return_value.discord_token = "tok"
        mock_cfg.return_value.github_username = ""

        mock_result = MagicMock()
        mock_result.output = "주간 리뷰 내용"
        mock_agent.run = AsyncMock(return_value=mock_result)

        await _weekly_review()

    mock_send.assert_awaited_once()
    args: Any = mock_send.await_args
    assert "주간 리뷰" in args[0][2]


# ── _commit_reminder ──────────────────────────────────────────────────────────


async def test_commit_reminder_skipped_no_username() -> None:
    with patch("app.services.scheduler.get_settings") as mock_cfg:
        mock_cfg.return_value.github_username = ""
        mock_cfg.return_value.discord_channel_id = "123"
        mock_cfg.return_value.discord_token = "tok"
        with patch("app.services.scheduler._send_discord_message") as send_mock:
            await _commit_reminder()
    send_mock.assert_not_called()


async def test_commit_reminder_skipped_when_commit_exists() -> None:
    today = date.today()
    fake_events = [
        {
            "type": "PushEvent",
            "created_at": datetime(today.year, today.month, today.day, 12, 0, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        }
    ]

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = fake_events

    class _FakeClient:
        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

        async def get(self, *_: Any, **__: Any) -> MagicMock:
            return mock_resp

    with (
        patch("app.services.scheduler.get_settings") as mock_cfg,
        patch("app.services.scheduler.httpx.AsyncClient", return_value=_FakeClient()),
        patch("app.services.scheduler._send_discord_message") as send_mock,
    ):
        mock_cfg.return_value.github_username = "testuser"
        mock_cfg.return_value.discord_channel_id = "123"
        mock_cfg.return_value.discord_token = "tok"
        await _commit_reminder()

    send_mock.assert_not_called()


async def test_commit_reminder_sends_when_no_commit() -> None:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = []  # no events

    class _FakeClient:
        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

        async def get(self, *_: Any, **__: Any) -> MagicMock:
            return mock_resp

    mock_send = AsyncMock()
    with (
        patch("app.services.scheduler.get_settings") as mock_cfg,
        patch("app.services.scheduler.httpx.AsyncClient", return_value=_FakeClient()),
        patch("app.services.scheduler._send_discord_message", mock_send),
    ):
        mock_cfg.return_value.github_username = "testuser"
        mock_cfg.return_value.discord_channel_id = "123"
        mock_cfg.return_value.discord_token = "tok"
        await _commit_reminder()

    mock_send.assert_awaited_once()
    args: Any = mock_send.await_args
    assert "커밋" in args[0][2]


async def test_commit_reminder_skips_on_api_failure() -> None:
    class _FailClient:
        async def __aenter__(self) -> _FailClient:
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

        async def get(self, *_: Any, **__: Any) -> None:
            raise ConnectionError("timeout")

    mock_send = AsyncMock()
    with (
        patch("app.services.scheduler.get_settings") as mock_cfg,
        patch("app.services.scheduler.httpx.AsyncClient", return_value=_FailClient()),
        patch("app.services.scheduler._send_discord_message", mock_send),
    ):
        mock_cfg.return_value.github_username = "testuser"
        mock_cfg.return_value.discord_channel_id = "123"
        mock_cfg.return_value.discord_token = "tok"
        await _commit_reminder()

    mock_send.assert_not_called()
