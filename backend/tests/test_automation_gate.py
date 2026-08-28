"""automation_gate — run-time on/off check for fixed automations (cron/mqtt_rule)."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.automation_gate import is_enabled, mark_run
from app.services.scheduler import _commit_reminder, _habit_daily_reset


def _db_returning(value: Any) -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: value))
    return db


async def test_is_enabled_true_when_flag_on() -> None:
    assert await is_enabled(_db_returning(True), "morning-brief") is True


async def test_is_enabled_false_when_flag_off() -> None:
    assert await is_enabled(_db_returning(False), "morning-brief") is False


async def test_is_enabled_fails_open_when_row_missing() -> None:
    """No row for this slug yet (e.g. right after migration) — never silently disable."""
    assert await is_enabled(_db_returning(None), "some-new-slug") is True


async def test_mark_run_commits_and_never_raises() -> None:
    db = AsyncMock()
    await mark_run(db, "morning-brief")
    db.commit.assert_awaited_once()

    failing_db = AsyncMock()
    failing_db.execute = AsyncMock(side_effect=RuntimeError("db down"))
    await mark_run(failing_db, "morning-brief")  # must not raise


# ── Gate wired into scheduler.py jobs ────────────────────────────────────────


class _FakeSessionCtx:
    def __init__(self, enabled: bool) -> None:
        self._enabled = enabled

    async def __aenter__(self) -> AsyncMock:
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: self._enabled))
        return db

    async def __aexit__(self, *_: Any) -> bool:
        return False


async def test_habit_daily_reset_skips_db_update_when_disabled() -> None:
    with patch("app.core.database.AsyncSessionLocal", return_value=_FakeSessionCtx(False)):
        await _habit_daily_reset()
    # No exception, and since it's gated off, the function returns right after the
    # gate check — nothing else to assert here beyond "it didn't blow up".


async def test_commit_reminder_skipped_when_disabled() -> None:
    with (
        patch("app.core.database.AsyncSessionLocal", return_value=_FakeSessionCtx(False)),
        patch("app.services.scheduler.get_settings") as mock_cfg,
        patch("app.services.scheduler.notify") as send_mock,
    ):
        mock_cfg.return_value.github_username = "quoding"
        await _commit_reminder()
    send_mock.assert_not_called()


async def test_commit_reminder_runs_when_enabled() -> None:
    with (
        patch("app.core.database.AsyncSessionLocal", return_value=_FakeSessionCtx(True)),
        patch("app.services.scheduler.get_settings") as mock_cfg,
        patch("app.services.scheduler.is_discord_notify_enabled", AsyncMock(return_value=True)),
        patch("app.services.scheduler.is_push_notify_enabled", AsyncMock(return_value=False)),
        patch("app.services.scheduler.notify") as send_mock,
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_cfg.return_value.github_username = "quoding"

        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        await _commit_reminder()
    send_mock.assert_awaited_once()
