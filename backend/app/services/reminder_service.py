"""Reminder service — parse, CRUD, polling loop, fire."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from croniter import croniter
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.models.reminder import Reminder

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 10  # seconds
_ESCALATION_MINUTES = 30  # DM escalation after N minutes without reaction


# ── Time parsing ──────────────────────────────────────────────────────────────

def _try_dateparser(text: str) -> datetime | None:
    """빠른 1차 파싱 — 단순 datetime 표현만."""
    try:
        import dateparser
        result = dateparser.parse(
            text,
            languages=["ko", "en"],
            settings={
                "PREFER_FUTURE_DATES": True,
                "RETURN_AS_TIMEZONE_AWARE": True,
                "TIMEZONE": "Asia/Seoul",
            },
        )
        return result
    except Exception:
        return None


_RECURRENCE_KEYWORDS = ("매일", "매주", "매월", "every", "daily", "weekly", "monthly", "격주")


async def parse_reminder_time(text: str) -> dict[str, Any]:
    """
    Returns:
        {"fire_at": datetime, "cron_expr": str | None, "error": str | None}
    """
    has_recurrence = any(kw in text for kw in _RECURRENCE_KEYWORDS)

    if not has_recurrence:
        parsed = _try_dateparser(text)
        if parsed:
            return {"fire_at": parsed, "cron_expr": None, "error": None}

    # LLM fallback — GPT-5.4 nano
    return await _llm_parse(text)


async def _llm_parse(text: str) -> dict[str, Any]:
    now_kst = datetime.now(timezone.utc).astimezone(
        __import__("zoneinfo").ZoneInfo("Asia/Seoul")
    )
    prompt = f"""현재 시각: {now_kst.strftime('%Y-%m-%d %H:%M')} (KST)

다음 알림 시간 표현을 파싱해서 JSON으로 반환해줘:
"{text}"

규칙:
- fire_at: 다음 발송 시각 (ISO8601, timezone 포함)
- cron_expr: 반복 알림이면 cron 표현식 (5필드, null이면 일회성)
- is_vague: true이면 시간 표현이 애매함
- error: 파싱 불가능하면 이유

예시:
- "매일 오전 9시" → {{"fire_at": "2026-06-07T09:00:00+09:00", "cron_expr": "0 9 * * *", "is_vague": false, "error": null}}
- "매주 월요일 오후 3시" → {{"fire_at": "...", "cron_expr": "0 15 * * 1", "is_vague": false, "error": null}}
- "30분 후" → {{"fire_at": "...", "cron_expr": null, "is_vague": false, "error": null}}
- "좀 이따가" → {{"fire_at": null, "cron_expr": null, "is_vague": true, "error": "시간이 불명확합니다"}}

JSON만 반환 (설명 없이):"""

    try:
        from openai import AsyncOpenAI
        settings = get_settings()
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model=settings.openai_model_default,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_completion_tokens=200,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")

        fire_at = None
        if data.get("fire_at"):
            fire_at = datetime.fromisoformat(data["fire_at"])

        return {
            "fire_at": fire_at,
            "cron_expr": data.get("cron_expr"),
            "is_vague": data.get("is_vague", False),
            "error": data.get("error"),
        }
    except Exception as exc:
        logger.warning("LLM time parse failed: %s", exc)
        return {"fire_at": None, "cron_expr": None, "error": str(exc)}


# ── CRUD ──────────────────────────────────────────────────────────────────────

async def create_reminder(
    db: AsyncSession,
    *,
    discord_user_id: str,
    discord_channel_id: str | None,
    content: str,
    fire_at: datetime,
    cron_expr: str | None = None,
) -> Reminder:
    r = Reminder(
        discord_user_id=discord_user_id,
        discord_channel_id=discord_channel_id,
        content=content,
        fire_at=fire_at,
        cron_expr=cron_expr,
    )
    db.add(r)
    await db.flush()
    await db.commit()
    await db.refresh(r)
    return r


async def list_reminders(db: AsyncSession, discord_user_id: str) -> list[Reminder]:
    res = await db.execute(
        select(Reminder)
        .where(Reminder.discord_user_id == discord_user_id, Reminder.done == False)
        .order_by(Reminder.fire_at)
    )
    return list(res.scalars().all())


async def delete_reminder(db: AsyncSession, reminder_id: int, discord_user_id: str) -> bool:
    res = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.discord_user_id == discord_user_id,
        )
    )
    r = res.scalar_one_or_none()
    if not r:
        return False
    await db.delete(r)
    await db.commit()
    return True


async def snooze_reminder(
    db: AsyncSession, reminder_id: int, snooze_minutes: int
) -> Reminder | None:
    res = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
    r = res.scalar_one_or_none()
    if not r:
        return None

    new_fire_at = datetime.now(timezone.utc) + timedelta(minutes=snooze_minutes)
    r.fire_at = new_fire_at
    r.fired = False
    r.snooze_count += 1
    await db.commit()
    await db.refresh(r)
    return r


async def mark_done(db: AsyncSession, reminder_id: int) -> None:
    await db.execute(
        update(Reminder).where(Reminder.id == reminder_id).values(done=True)
    )
    await db.commit()


# ── Next fire for recurring reminders ─────────────────────────────────────────

def _next_fire(cron_expr: str) -> datetime:
    cron = croniter(cron_expr, datetime.now(timezone.utc))
    return cron.get_next(datetime)


# ── Polling loop ──────────────────────────────────────────────────────────────

# Bot instance injected at startup
_bot: Any = None


def set_bot(bot: Any) -> None:
    global _bot
    _bot = bot


async def _fire_reminder(db_factory: async_sessionmaker[AsyncSession], reminder: Reminder) -> None:
    """알림 발송 + 반복 알림 재스케줄."""
    if _bot is None:
        logger.warning("Bot not set, cannot fire reminder %d", reminder.id)
        return

    async with db_factory() as db:
        # 발송 처리
        await db.execute(
            update(Reminder).where(Reminder.id == reminder.id).values(fired=True)
        )

        # 반복 알림이면 다음 fire_at 계산
        if reminder.cron_expr:
            next_dt = _next_fire(reminder.cron_expr)
            await db.execute(
                update(Reminder).where(Reminder.id == reminder.id).values(
                    fire_at=next_dt, fired=False
                )
            )

        await db.commit()

    # Discord 발송은 bot에 위임
    try:
        await _bot.send_reminder(reminder)
    except Exception:
        logger.exception("Failed to send reminder %d via Discord", reminder.id)


async def reminder_poll_loop(db_factory: async_sessionmaker[AsyncSession]) -> None:
    """10초마다 due 알림 확인 후 발송."""
    logger.info("Reminder polling loop started")
    while True:
        try:
            now = datetime.now(timezone.utc)
            async with db_factory() as db:
                res = await db.execute(
                    select(Reminder).where(
                        Reminder.fire_at <= now,
                        Reminder.fired == False,
                        Reminder.done == False,
                    )
                )
                due = list(res.scalars().all())

            for r in due:
                asyncio.create_task(_fire_reminder(db_factory, r))

        except Exception:
            logger.exception("Reminder poll error")

        await asyncio.sleep(_POLL_INTERVAL)
