from __future__ import annotations

import logging
import time
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import get_settings
from app.services.discord_notify import send_discord_message as _send_discord_message

logger = logging.getLogger(__name__)

_KST = ZoneInfo("Asia/Seoul")

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

# 회의 5분 전 알림 — 오늘 하루 이미 알린 이벤트 id를 기억해 중복 발송 방지.
# 매일 00:01 habit-daily-reset 잡에서 같이 비운다 (레코드별 fire_at을 관리하는 게
# 아니라 고정 주기(1분)로 폴링하는 방식이라 CLAUDE.md의 "동적 리마인더에
# APScheduler 금지" 규칙과 무관 — sensor-poll과 같은 패턴).
_alerted_meeting_ids: set[str] = set()


async def _automation_enabled(slug: str) -> bool:
    """Gate for fixed automations toggled from the 자동화 page — see automation_gate.py."""
    from app.core.database import AsyncSessionLocal
    from app.services.automation_gate import is_enabled

    try:
        async with AsyncSessionLocal() as db:
            enabled = await is_enabled(db, slug)
    except Exception:
        logger.warning("Automation gate check failed for %s, running anyway", slug, exc_info=True)
        return True
    if not enabled:
        logger.info("Automation '%s' is disabled, skipping", slug)
    return enabled


async def _automation_mark_run(slug: str) -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.automation_gate import mark_run

    try:
        async with AsyncSessionLocal() as db:
            await mark_run(db, slug)
    except Exception:
        logger.warning("Failed to mark automation run for %s", slug, exc_info=True)


def _parse_hm(hm: str, default: tuple[int, int] = (16, 0)) -> tuple[int, int]:
    try:
        h, m = hm.split(":")
        return int(h), int(m)
    except (ValueError, AttributeError):
        logger.warning("Invalid HH:MM setting %r, falling back to %s", hm, default)
        return default


def start_scheduler() -> None:
    scheduler.add_job(
        _morning_brief,
        trigger=CronTrigger(hour=8, minute=0),
        id="morning-brief",
        replace_existing=True,
    )
    cutoff_hour, cutoff_minute = _parse_hm(get_settings().caffeine_cutoff)
    scheduler.add_job(
        _caffeine_cutoff_alert,
        trigger=CronTrigger(hour=cutoff_hour, minute=cutoff_minute),
        id="caffeine-cutoff-alert",
        replace_existing=True,
    )
    scheduler.add_job(
        _deadline_watch,
        trigger=CronTrigger(hour=9, minute=0),
        id="deadline-watch",
        replace_existing=True,
    )
    scheduler.add_job(
        _schedule_conflict_watch,
        trigger=CronTrigger(hour=7, minute=30),
        id="schedule-conflict-watch",
        replace_existing=True,
    )
    scheduler.add_job(
        _meeting_reminder_poll,
        trigger=IntervalTrigger(minutes=1),
        id="meeting-reminder-poll",
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
        _daily_summary,
        trigger=CronTrigger(hour=23, minute=30),
        id="daily-summary",
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
    if not await _automation_enabled("morning-brief"):
        return
    logger.info("Running morning brief")
    cfg = get_settings()
    if not cfg.discord_channel_id or not cfg.discord_token:
        logger.warning("Morning brief skipped: discord_channel_id or discord_token not configured")
        return

    try:
        from sqlalchemy import select

        from app.core.database import AsyncSessionLocal
        from app.models.agenda import Todo
        from app.services import google_calendar
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

        # Gather today's events from Google Calendar and uncompleted todos from DB
        today = date.today()
        events_text = ""
        todos_text = ""

        day_start = datetime(today.year, today.month, today.day, 0, 0, 0).isoformat() + "+09:00"
        day_end = datetime(today.year, today.month, today.day, 23, 59, 59).isoformat() + "+09:00"
        events = await google_calendar.list_events(day_start, day_end)
        if events:
            event_lines = [
                f"{'종일' if e['all_day'] else e['start'][11:16]} {e['title']}" for e in events
            ]
            events_text = "오늘 일정:\n" + "\n".join(f"- {line}" for line in event_lines)
        else:
            events_text = "오늘 일정 없음"

        async with AsyncSessionLocal() as db:
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
    await _automation_mark_run("morning-brief")


async def _sensor_poll() -> None:
    """Every 30s — request sensor data from ESP32 devices via MQTT."""
    from app.services.mqtt_bridge import mqtt_bridge

    await mqtt_bridge.publish("quark/cmd/all/poll", {"ts": time.time()})


async def _weekly_review() -> None:
    """Every Friday 17:00 KST — generate weekly review and send via Discord."""
    if not await _automation_enabled("weekly-review"):
        return
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
        # Find start of current week (Monday) — timedelta로 계산해야 월초에
        # day가 0 이하로 떨어지는 ValueError가 없다.
        monday = today - timedelta(days=today.weekday())
        week_start = datetime(monday.year, monday.month, monday.day, tzinfo=UTC)

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
    await _automation_mark_run("weekly-review")


async def _daily_summary() -> None:
    """매일 23:30 KST — 오늘의 모든 세션 대화를 요약해 daily_episodes에 저장.

    주간 리뷰와 아침 브리핑이 이 에피소드를 읽는다.
    """
    logger.info("Running daily summary")
    try:
        import redis.asyncio as aioredis

        from app.core.database import AsyncSessionLocal
        from app.core.redis import get_pool
        from app.services.rag import create_daily_summary_all

        redis = aioredis.Redis(connection_pool=get_pool())
        try:
            async with AsyncSessionLocal() as db:
                saved = await create_daily_summary_all(redis, db)
            logger.info("Daily summary %s", "saved" if saved else "skipped (no conversations)")
        finally:
            await redis.aclose()
    except Exception:
        logger.warning("Daily summary failed", exc_info=True)


async def _habit_daily_reset() -> None:
    """매일 00:01 KST — 모든 습관의 done_today를 False로 리셋 + 회의 알림 중복방지 셋 초기화."""
    _alerted_meeting_ids.clear()
    if not await _automation_enabled("habit-daily-reset"):
        return
    logger.info("Running habit daily reset")
    try:
        from sqlalchemy import update

        from app.core.database import AsyncSessionLocal
        from app.models.agenda import Habit

        async with AsyncSessionLocal() as db:
            await db.execute(update(Habit).values(done_today=False))
            await db.commit()
        logger.info("Habit daily reset complete")
        await _automation_mark_run("habit-daily-reset")
    except Exception:
        logger.warning("Habit daily reset failed", exc_info=True)


async def _caffeine_cutoff_alert() -> None:
    """카페인 컷오프 시각(설정값, 기본 16:00) — 오늘 카페인을 마셨으면 Discord로 알림.

    안 마신 날은 알릴 필요가 없으니 조용히 스킵.
    """
    logger.info("Running caffeine cutoff alert")
    cfg = get_settings()
    if not cfg.discord_channel_id or not cfg.discord_token:
        logger.warning("Caffeine cutoff alert skipped: discord not configured")
        return

    try:
        from sqlalchemy import func, select

        from app.core.database import AsyncSessionLocal
        from app.models.agenda import Alert, CaffeineLog

        today = date.today()
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(func.sum(CaffeineLog.amount_mg)).where(CaffeineLog.date == today)
            )
            total_mg: int = res.scalar_one() or 0
            if total_mg <= 0:
                logger.debug("Caffeine cutoff alert skipped: no caffeine logged today")
                return

            cups = total_mg // 100
            body = f"오늘 카페인 {cups}잔 마셨어. 컷오프 시간이야 — 이제 디카페인으로 바꾸자."
            db.add(Alert(title="카페인 컷오프", body=body, urgent=False))
            await db.commit()

        msg = f"☕ 카페인 컷오프 시간이야 ({cfg.caffeine_cutoff}) — 오늘 {cups}잔 마셨어. 이제 디카페인 권장!"
        await _send_discord_message(cfg.discord_channel_id, cfg.discord_token, msg)
        logger.info("Caffeine cutoff alert sent")
    except Exception:
        logger.warning("Caffeine cutoff alert failed", exc_info=True)


async def _deadline_watch() -> None:
    """Daily 09:00 KST — Discord 경고 for D-Day items due within 3 days.

    D-Day(`DdayItem`)를 마감 소스로 쓴다 — Todo에는 마감일 필드가 없고
    캘린더 이벤트엔 "마감"을 구분할 방법이 없어서, 실제로 날짜 기반 마감 추적이
    가능한 건 D-Day뿐이다.
    """
    logger.info("Running deadline watch")
    cfg = get_settings()
    if not cfg.discord_channel_id or not cfg.discord_token:
        logger.warning("Deadline watch skipped: discord not configured")
        return

    try:
        from sqlalchemy import select

        from app.core.database import AsyncSessionLocal
        from app.models.agenda import Alert, DdayItem

        today = date.today()
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(DdayItem).order_by(DdayItem.target_date))
            items = res.scalars().all()

            due_soon = [
                (item, (item.target_date - today).days)
                for item in items
                if 0 <= (item.target_date - today).days <= 3
            ]
            if not due_soon:
                logger.debug("Deadline watch: nothing due within 3 days")
                return

            lines = [f"- {item.label}: D-{days}" for item, days in due_soon]
            for item, days in due_soon:
                db.add(
                    Alert(
                        title=f"마감 임박: {item.label}",
                        body=f"D-{days} 남았어.",
                        urgent=days <= 1,
                    )
                )
            await db.commit()

        msg = "⏰ 3일 내 마감 임박:\n" + "\n".join(lines)
        await _send_discord_message(cfg.discord_channel_id, cfg.discord_token, msg)
        logger.info("Deadline watch sent (%d item(s))", len(due_soon))
    except Exception:
        logger.warning("Deadline watch failed", exc_info=True)


async def _schedule_conflict_watch() -> None:
    """Daily 07:30 KST — Discord 경고 for overlapping events on today's Google Calendar.

    종일(all-day) 일정은 시간 개념이 없어 겹침 판정에서 제외한다.
    """
    logger.info("Running schedule conflict watch")
    cfg = get_settings()
    if not cfg.discord_channel_id or not cfg.discord_token:
        logger.warning("Schedule conflict watch skipped: discord not configured")
        return

    try:
        from app.services import google_calendar

        today = date.today()
        day_start = datetime(today.year, today.month, today.day, 0, 0, 0).isoformat() + "+09:00"
        day_end = datetime(today.year, today.month, today.day, 23, 59, 59).isoformat() + "+09:00"
        events = await google_calendar.list_events(day_start, day_end)

        timed = sorted(
            (e for e in events if not e["all_day"] and e["start"] and e["end"]),
            key=lambda e: e["start"],
        )

        conflicts: list[tuple[dict, dict]] = []
        for a, b in zip(timed, timed[1:]):
            if datetime.fromisoformat(b["start"]) < datetime.fromisoformat(a["end"]):
                conflicts.append((a, b))

        if not conflicts:
            logger.debug("Schedule conflict watch: no overlaps today")
            return

        from app.core.database import AsyncSessionLocal
        from app.models.agenda import Alert

        def _hm(iso: str) -> str:
            return iso[11:16] if len(iso) >= 16 else iso

        lines = [
            f"- {a['title']}({_hm(a['start'])}~{_hm(a['end'])}) ↔ {b['title']}({_hm(b['start'])}~{_hm(b['end'])})"
            for a, b in conflicts
        ]
        async with AsyncSessionLocal() as db:
            for a, b in conflicts:
                db.add(
                    Alert(
                        title="일정 겹침",
                        body=f"{a['title']} / {b['title']} 시간이 겹쳐.",
                        urgent=True,
                    )
                )
            await db.commit()

        msg = "⚠️ 오늘 일정이 겹쳐:\n" + "\n".join(lines)
        await _send_discord_message(cfg.discord_channel_id, cfg.discord_token, msg)
        logger.info("Schedule conflict watch sent (%d conflict(s))", len(conflicts))
    except Exception:
        logger.warning("Schedule conflict watch failed", exc_info=True)


async def _meeting_reminder_poll() -> None:
    """1분마다 — 5분 이내 시작하는(0~5분) 오늘 캘린더 이벤트에 Discord 알림.

    이미 알린 이벤트는 `_alerted_meeting_ids`로 중복 방지 (00:01에 초기화됨).
    """
    cfg = get_settings()
    if not cfg.discord_channel_id or not cfg.discord_token:
        return

    try:
        from app.services import google_calendar

        now = datetime.now(_KST)
        window_end = now + timedelta(minutes=6)
        events = await google_calendar.list_events(now.isoformat(), window_end.isoformat())

        for e in events:
            if e["all_day"] or not e["start"] or e["id"] in _alerted_meeting_ids:
                continue
            start = datetime.fromisoformat(e["start"])
            minutes_until = (start - now).total_seconds() / 60
            if 0 <= minutes_until <= 5:
                _alerted_meeting_ids.add(e["id"])
                msg = f"🔔 {start.strftime('%H:%M')} \"{e['title']}\" 5분 전이야 — 준비해!"
                await _send_discord_message(cfg.discord_channel_id, cfg.discord_token, msg)
                logger.info("Meeting reminder sent for event %s", e["id"])
    except Exception:
        logger.warning("Meeting reminder poll failed", exc_info=True)


async def _commit_reminder() -> None:
    """Daily 23:00 KST — send Discord alert if no commits today.

    Skips silently if settings.github_username is empty.
    """
    if not await _automation_enabled("commit-reminder"):
        return
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
    await _automation_mark_run("commit-reminder")
