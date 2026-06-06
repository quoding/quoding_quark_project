from __future__ import annotations

import logging
from datetime import UTC, date, datetime

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


def start_scheduler() -> None:
    scheduler.add_job(
        _morning_brief,
        trigger=CronTrigger(hour=8, minute=0),
        id="morning-brief",
        replace_existing=True,
    )
    scheduler.add_job(
        _sensor_poll,
        trigger=IntervalTrigger(seconds=30),
        id="sensor-poll",
        replace_existing=True,
    )
    scheduler.add_job(
        _weekly_review,
        trigger=CronTrigger(day_of_week="fri", hour=17, minute=0),
        id="weekly-review",
        replace_existing=True,
    )
    scheduler.add_job(
        _commit_reminder,
        trigger=CronTrigger(hour=23, minute=0),
        id="commit-reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        _habit_daily_reset,
        trigger=CronTrigger(hour=0, minute=1),
        id="habit-daily-reset",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — %d jobs registered", len(scheduler.get_jobs()))


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)


async def _morning_brief() -> None:
    """Daily 08:00 KST — generate and send enhanced morning summary via Discord."""
    logger.info("Running morning brief")
    cfg = get_settings()
    if not cfg.discord_channel_id or not cfg.discord_token:
        logger.warning("Morning brief skipped: discord_channel_id or discord_token not configured")
        return

    try:
        from sqlalchemy import select

        from app.core.database import AsyncSessionLocal
        from app.models.agenda import ScheduledEvent, Todo
        from app.services.weather import get_current_weather

        # Gather real weather
        weather = await get_current_weather()
        weather_text: str
        if "error" in weather:
            weather_text = "날씨 정보를 가져오지 못했어."
        else:
            weather_text = (
                f"현재 {weather['temp']}°C, {weather['label']}. "
                f"최고 {weather['hi']}° / 최저 {weather['lo']}°. "
                f"미세먼지 PM2.5 {weather['pm25']} ({weather['aqi_grade']})"
            )

        # Gather today's events and uncompleted todos from DB
        today = date.today()
        events_text = ""
        todos_text = ""

        async with AsyncSessionLocal() as db:
            day_start = datetime(today.year, today.month, today.day, tzinfo=UTC)
            day_end = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=UTC)

            ev_result = await db.execute(
                select(ScheduledEvent)
                .where(ScheduledEvent.scheduled_at >= day_start)
                .where(ScheduledEvent.scheduled_at <= day_end)
                .order_by(ScheduledEvent.scheduled_at)
            )
            events = ev_result.scalars().all()
            if events:
                event_lines = [f"{e.scheduled_at.strftime('%H:%M')} {e.title} [{e.tag}]" for e in events]
                events_text = "오늘 일정:\n" + "\n".join(f"- {line}" for line in event_lines)
            else:
                events_text = "오늘 일정 없음"

            todo_result = await db.execute(
                select(Todo).where(Todo.done.is_(False)).order_by(Todo.created_at)
            )
            pending_todos = todo_result.scalars().all()
            if pending_todos:
                todo_lines = [t.text for t in pending_todos[:5]]
                todos_text = "미완료 할 일:\n" + "\n".join(f"- {t}" for t in todo_lines)
            else:
                todos_text = "미완료 할 일 없음"

        extra_context = f"[날씨]\n{weather_text}\n\n[일정]\n{events_text}\n\n[할일]\n{todos_text}"

        from app.agents.deps import QuarkDeps
        from app.agents.quark_agent import quark_agent
        from app.services.mqtt_bridge import mqtt_bridge

        result = await quark_agent.run(
            f"오늘은 {today.isoformat()}이야. "
            "아침 브리핑을 날씨·일정·할일 섹션으로 나눠서 간결하게 한국어로 만들어줘.\n\n"
            f"{extra_context}",
            deps=QuarkDeps(mqtt=mqtt_bridge),
        )
        content = result.output
    except Exception:
        logger.warning("Morning brief: content generation failed", exc_info=True)
        return

    await _send_discord_message(cfg.discord_channel_id, cfg.discord_token, content)


async def _send_discord_message(channel_id: str, token: str, content: str) -> None:
    """Send *content* to a Discord channel using the bot REST API (no gateway)."""
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url, json={"content": content[:2000]}, headers=headers, timeout=10.0
            )
            resp.raise_for_status()
        logger.info("Message sent to Discord channel %s", channel_id)
    except Exception:
        logger.warning("Discord send failed", exc_info=True)


async def _sensor_poll() -> None:
    """Every 30s — request sensor data from ESP32 devices via MQTT."""
    from app.services.mqtt_bridge import mqtt_bridge

    await mqtt_bridge.publish("quark/cmd/all/poll", {"ts": __import__("time").time()})


async def _weekly_review() -> None:
    """Every Friday 17:00 KST — generate weekly review and send via Discord."""
    logger.info("Running weekly review")
    cfg = get_settings()
    if not cfg.discord_channel_id or not cfg.discord_token:
        logger.warning("Weekly review skipped: discord not configured")
        return

    try:
        from sqlalchemy import select

        from app.core.database import AsyncSessionLocal
        from app.models.agenda import Habit, Todo
        from app.models.memory import DailyEpisode

        today = date.today()
        # Find start of current week (Monday)
        week_start = datetime(today.year, today.month, today.day, tzinfo=UTC)
        week_start = week_start.replace(
            day=today.day - today.weekday(),
            hour=0,
            minute=0,
            second=0,
        )

        async with AsyncSessionLocal() as db:
            # Get this week's daily episodes
            ep_result = await db.execute(
                select(DailyEpisode)
                .where(DailyEpisode.date >= week_start.date())
                .order_by(DailyEpisode.date)
            )
            episodes = ep_result.scalars().all()
            ep_context = ""
            if episodes:
                ep_context = "\n".join(
                    f"- {e.date}: {str(e.summary.get('text', ''))[:150]}"
                    for e in episodes
                )

            # Get completed todos this week
            todo_result = await db.execute(
                select(Todo).where(Todo.done.is_(True)).order_by(Todo.created_at)
            )
            done_todos = todo_result.scalars().all()
            todo_context = "\n".join(f"- {t.text}" for t in done_todos[:10]) or "없음"

            # Get habits and streaks
            habit_result = await db.execute(select(Habit).order_by(Habit.streak.desc()))
            habits = habit_result.scalars().all()
            habit_context = "\n".join(
                f"- {h.name}: {h.streak}일 스트릭" for h in habits[:5]
            ) or "없음"

        from app.agents.deps import QuarkDeps
        from app.agents.quark_agent import quark_agent
        from app.services.mqtt_bridge import mqtt_bridge

        result = await quark_agent.run(
            f"이번 주({week_start.date().isoformat()} ~ {today.isoformat()}) 주간 리뷰를 한국어로 작성해줘.\n\n"
            f"[일별 요약]\n{ep_context or '없음'}\n\n"
            f"[완료한 할 일]\n{todo_context}\n\n"
            f"[습관 스트릭]\n{habit_context}",
            deps=QuarkDeps(mqtt=mqtt_bridge),
        )
        content = result.output
    except Exception:
        logger.warning("Weekly review: content generation failed", exc_info=True)
        return

    await _send_discord_message(cfg.discord_channel_id, cfg.discord_token, content)


async def _habit_daily_reset() -> None:
    """매일 00:01 KST — 모든 습관의 done_today를 False로 리셋."""
    logger.info("Running habit daily reset")
    try:
        from sqlalchemy import update

        from app.core.database import AsyncSessionLocal
        from app.models.agenda import Habit

        async with AsyncSessionLocal() as db:
            await db.execute(update(Habit).values(done_today=False))
            await db.commit()
        logger.info("Habit daily reset complete")
    except Exception:
        logger.warning("Habit daily reset failed", exc_info=True)


async def _commit_reminder() -> None:
    """Daily 23:00 KST — send Discord alert if no commits today.

    Skips silently if settings.github_username is empty.
    """
    cfg = get_settings()
    if not cfg.github_username:
        logger.debug("Commit reminder skipped: github_username not configured")
        return
    if not cfg.discord_channel_id or not cfg.discord_token:
        logger.warning("Commit reminder skipped: discord not configured")
        return

    today = date.today()
    has_commit = False
    try:
        url = f"https://api.github.com/users/{cfg.github_username}/events"
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers={"Accept": "application/vnd.github+json"})
            resp.raise_for_status()
            events: list[dict[str, object]] = resp.json()

        for ev in events:
            if ev.get("type") == "PushEvent":
                created_raw = ev.get("created_at")
                if isinstance(created_raw, str):
                    created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                    if created.date() == today:
                        has_commit = True
                        break
    except Exception:
        logger.warning("Commit reminder: GitHub API call failed", exc_info=True)
        return

    if not has_commit:
        msg = f"🔔 오늘 커밋이 없어! ({today.isoformat()}) 코드 한 줄이라도 남겨두자."
        await _send_discord_message(cfg.discord_channel_id, cfg.discord_token, msg)
        logger.info("Commit reminder sent")
