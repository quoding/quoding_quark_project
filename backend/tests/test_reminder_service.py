"""Tests for reminder_service — time parsing + CRUD (no real network calls)."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import reminder_service


# ── parse_reminder_time ───────────────────────────────────────────────────────

class TestDateparserPath:
    """단순 시간 표현은 dateparser 경로로 처리."""

    @pytest.mark.asyncio
    async def test_simple_absolute(self):
        with patch("dateparser.parse") as mock_dp:
            mock_dp.return_value = datetime(2026, 6, 7, 9, 0, tzinfo=timezone.utc)
            result = await reminder_service.parse_reminder_time("내일 오전 9시")

        assert result["fire_at"] == datetime(2026, 6, 7, 9, 0, tzinfo=timezone.utc)
        assert result["cron_expr"] is None
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_dateparser_failure_falls_back_to_llm(self):
        with patch("dateparser.parse", return_value=None):
            with patch.object(reminder_service, "_llm_parse", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = {
                    "fire_at": datetime(2026, 6, 7, 14, 0, tzinfo=timezone.utc),
                    "cron_expr": None,
                    "error": None,
                }
                result = await reminder_service.parse_reminder_time("오후 2시")

        mock_llm.assert_awaited_once()
        assert result["fire_at"] is not None


class TestLlmPath:
    """반복 키워드는 무조건 LLM 경로."""

    @pytest.mark.asyncio
    async def test_recurrence_goes_to_llm(self):
        with patch.object(reminder_service, "_llm_parse", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "fire_at": datetime(2026, 6, 7, 9, 0, tzinfo=timezone.utc),
                "cron_expr": "0 9 * * *",
                "is_vague": False,
                "error": None,
            }
            result = await reminder_service.parse_reminder_time("매일 오전 9시 약먹기")

        mock_llm.assert_awaited_once()
        assert result["cron_expr"] == "0 9 * * *"

    @pytest.mark.asyncio
    async def test_llm_openai_called_correctly(self):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = (
            '{"fire_at": "2026-06-07T09:00:00+09:00", "cron_expr": "0 9 * * *", '
            '"is_vague": false, "error": null}'
        )
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

        with patch("app.services.reminder_service.get_settings") as mock_settings:
            mock_settings.return_value.openai_api_key = "sk-test"
            mock_settings.return_value.openai_model_default = "gpt-5.4-nano"
            with patch("openai.AsyncOpenAI", return_value=mock_client):
                result = await reminder_service._llm_parse("매일 오전 9시")

        assert result["cron_expr"] == "0 9 * * *"
        assert result["error"] is None
        assert result["fire_at"] is not None


# ── _next_fire ────────────────────────────────────────────────────────────────

class TestNextFire:
    def test_daily_cron(self):
        # "0 9 * * *" should return a future datetime
        result = reminder_service._next_fire("0 9 * * *")
        assert isinstance(result, datetime)
        assert result > datetime.now(timezone.utc)

    def test_weekly_cron(self):
        result = reminder_service._next_fire("0 15 * * 1")
        assert isinstance(result, datetime)


# ── CRUD (DB mocked) ──────────────────────────────────────────────────────────

class TestCrud:
    @pytest.mark.asyncio
    async def test_create_reminder(self):
        mock_db = AsyncMock()
        mock_reminder = MagicMock()
        mock_reminder.id = 42

        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        fire_at = datetime(2026, 6, 7, 9, 0, tzinfo=timezone.utc)

        with patch("app.services.reminder_service.Reminder", return_value=mock_reminder):
            r = await reminder_service.create_reminder(
                mock_db,
                discord_user_id="12345",
                discord_channel_id="67890",
                content="약 먹기",
                fire_at=fire_at,
            )

        mock_db.add.assert_called_once_with(mock_reminder)
        mock_db.flush.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_snooze_adds_time(self):
        mock_reminder = MagicMock()
        mock_reminder.snooze_count = 0
        mock_reminder.fire_at = datetime(2026, 6, 7, 9, 0, tzinfo=timezone.utc)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_reminder)

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        r = await reminder_service.snooze_reminder(mock_db, reminder_id=1, snooze_minutes=10)

        assert mock_reminder.snooze_count == 1
        assert mock_reminder.fired is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        deleted = await reminder_service.delete_reminder(mock_db, 999, "12345")
        assert deleted is False
