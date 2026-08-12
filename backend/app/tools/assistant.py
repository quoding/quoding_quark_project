"""Personal-assistant function tools for the QUARK agent.

일정(events)은 Google Calendar를 단일 소스로 사용하고, todos/ideas/habits 등은
DB에 저장한다 (DB 작업은 ctx.deps.db가 None이 아니어야 함). 그 외 웹 검색 등도 포함.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from duckduckgo_search import DDGS
from pydantic_ai import RunContext
from sqlalchemy import select

from app.agents.deps import QuarkDeps

if TYPE_CHECKING:
    from pydantic_ai import Agent

logger = logging.getLogger(__name__)


async def add_event(
    ctx: RunContext[QuarkDeps],
    title: str,
    scheduled_at: str,
    end_at: str | None = None,
) -> str:
    """Google 캘린더에 일정을 추가한다 (아이폰 캘린더 앱과 자동 동기화됨).

    Args:
        title: 일정 제목.
        scheduled_at: 시작 시각, ISO 8601 (예: 2026-06-10T14:00:00). 타임존 생략 시 한국 시간(Asia/Seoul)으로 처리.
        end_at: 종료 시각, ISO 8601. 생략 시 시작 시각 + 1시간.
    """
    from app.services import google_calendar

    try:
        ev = await google_calendar.create_event(title, scheduled_at, end_at)
    except (ValueError, google_calendar.GoogleCalendarError) as exc:
        return f"일정 저장 실패: {exc}"
    return f"일정 저장했어: {ev['title']} ({ev['start']})"


async def list_events(
    ctx: RunContext[QuarkDeps],
    target_date: str | None = None,
) -> str:
    """Google 캘린더에서 일정 목록을 조회한다 (응답에 포함된 [id]는 수정/취소 시 그대로 사용).

    Args:
        target_date: 조회할 날짜 (YYYY-MM-DD). 생략 시 오늘.
    """
    from app.services import google_calendar

    try:
        d = date.fromisoformat(target_date) if target_date else date.today()
    except ValueError as exc:
        return f"날짜 형식 오류: {exc}"

    day_start = datetime(d.year, d.month, d.day, 0, 0, 0).isoformat() + "+09:00"
    day_end = datetime(d.year, d.month, d.day, 23, 59, 59).isoformat() + "+09:00"
    events = await google_calendar.list_events(day_start, day_end)
    if not events:
        return f"{d.isoformat()} 일정 없음"

    lines = []
    for e in events:
        when = "종일" if e["all_day"] else (e["start"][11:16] if len(e["start"]) >= 16 else e["start"])
        lines.append(f"- [{e['id']}] {when} {e['title']}")
    return f"{d.isoformat()} 일정:\n" + "\n".join(lines)


async def update_event(
    ctx: RunContext[QuarkDeps],
    event_id: str,
    title: str | None = None,
    scheduled_at: str | None = None,
    end_at: str | None = None,
) -> str:
    """기존 일정을 수정한다. event_id는 list_events 응답의 [id]를 그대로 사용.

    Args:
        event_id: 수정할 일정의 ID (list_events 결과의 대괄호 안 값).
        title: 새 제목 (생략 시 변경 안 함).
        scheduled_at: 새 시작 시각, ISO 8601 (생략 시 변경 안 함).
        end_at: 새 종료 시각, ISO 8601 (생략 시 변경 안 함).
    """
    from app.services import google_calendar

    try:
        ev = await google_calendar.update_event(event_id, title=title, start=scheduled_at, end=end_at)
    except (ValueError, google_calendar.GoogleCalendarError) as exc:
        return f"일정 수정 실패: {exc}"
    return f"일정 수정했어: {ev['title']} ({ev['start']})"


async def cancel_event(ctx: RunContext[QuarkDeps], event_id: str) -> str:
    """일정을 취소(삭제)한다. event_id는 list_events 응답의 [id]를 그대로 사용.

    Args:
        event_id: 취소할 일정의 ID (list_events 결과의 대괄호 안 값).
    """
    from app.services import google_calendar

    try:
        await google_calendar.delete_event(event_id)
    except google_calendar.GoogleCalendarError as exc:
        return f"일정 취소 실패: {exc}"
    return "일정 취소했어"


async def add_todo(ctx: RunContext[QuarkDeps], text: str) -> str:
    """할 일을 DB에 저장한다.

    Args:
        text: 할 일 내용.
    """
    if ctx.deps.db is None:
        return "할 일 저장 불가 (DB 연결 없음)"
    from app.models.agenda import Todo

    todo = Todo(text=text)
    ctx.deps.db.add(todo)
    await ctx.deps.db.flush()
    await ctx.deps.db.commit()
    return f"할 일 저장했어: {text}"


async def complete_todo(ctx: RunContext[QuarkDeps], todo_id: int) -> str:
    """할 일을 완료 처리한다.

    Args:
        todo_id: 완료할 할 일의 ID.
    """
    if ctx.deps.db is None:
        return "할 일 업데이트 불가 (DB 연결 없음)"
    from app.models.agenda import Todo

    result = await ctx.deps.db.execute(select(Todo).where(Todo.id == todo_id))
    todo = result.scalar_one_or_none()
    if todo is None:
        return f"할 일 ID {todo_id} 없음"
    todo.done = True
    await ctx.deps.db.flush()
    await ctx.deps.db.commit()
    return f"완료 처리했어: {todo.text}"


async def add_idea(
    ctx: RunContext[QuarkDeps],
    text: str,
    tag: str = "아이디어",
) -> str:
    """아이디어를 DB에 저장한다.

    Args:
        text: 아이디어 내용.
        tag: 태그 (선택).
    """
    if ctx.deps.db is None:
        return "아이디어 저장 불가 (DB 연결 없음)"
    from app.models.agenda import Idea

    idea = Idea(text=text, tag=tag)
    ctx.deps.db.add(idea)
    await ctx.deps.db.flush()
    await ctx.deps.db.commit()
    return f"아이디어 저장했어: {text}"


async def web_search(ctx: RunContext[QuarkDeps], query: str) -> str:
    """DuckDuckGo로 검색해 상위 5개 결과를 요약 반환한다.

    Args:
        query: 검색어.
    """
    try:
        results: list[dict[str, Any]] = list(DDGS().text(query, max_results=5))
        if not results:
            return "검색 결과 없음"
        lines = [f"{i + 1}. {r.get('title', '')} — {r.get('body', '')[:120]}" for i, r in enumerate(results)]
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("web_search failed: %s", exc)
        return "검색 결과 없음"


async def get_weather(ctx: RunContext[QuarkDeps]) -> str:
    """현재 날씨·기온·미세먼지를 조회한다 (대시보드 날씨 위젯과 같은 소스)."""
    from app.services.weather import get_current_weather

    data = await get_current_weather()
    if "error" in data:
        return "날씨 조회 실패 — 잠시 후 다시 시도해줘."
    return (
        f"{data['city']}: {data['label']}, 현재 {data['temp']}°C "
        f"(최고 {data['hi']}°C / 최저 {data['lo']}°C), "
        f"미세먼지 {data['pm25']}㎍/㎥ ({data['aqi_grade']})"
    )


async def add_habit(ctx: RunContext[QuarkDeps], name: str) -> str:
    """반복 습관을 DB에 등록한다.

    Args:
        name: 습관 이름 (예: 비타민 먹기, 물 2L 마시기).
    """
    if ctx.deps.db is None:
        return "습관 저장 불가 (DB 연결 없음)"
    from app.models.agenda import Habit

    habit = Habit(name=name, streak=0, done_today=False, last_checked_date=None)
    ctx.deps.db.add(habit)
    await ctx.deps.db.flush()
    await ctx.deps.db.commit()
    return f"습관 등록했어: {name}"


async def list_habits(ctx: RunContext[QuarkDeps]) -> str:
    """등록된 습관 목록과 오늘 완료 여부를 반환한다."""
    if ctx.deps.db is None:
        return "습관 조회 불가 (DB 연결 없음)"
    from app.models.agenda import Habit

    result = await ctx.deps.db.execute(select(Habit).order_by(Habit.created_at))
    habits = result.scalars().all()
    if not habits:
        return "등록된 습관 없음"
    lines = [
        f"- {'✅' if h.done_today else '⬜'} {h.name} (스트릭 {h.streak}일)"
        for h in habits
    ]
    return "습관 목록:\n" + "\n".join(lines)


async def log_mood(
    ctx: RunContext[QuarkDeps],
    score: int,
    note: str = "",
) -> str:
    """오늘 기분을 기록한다.

    Args:
        score: 기분 점수 1-5 (1=매우나쁨, 5=매우좋음).
        note: 추가 메모 (선택).
    """
    if ctx.deps.db is None:
        return "기분 저장 불가 (DB 연결 없음)"
    if not 1 <= score <= 5:
        return "score는 1-5 사이여야 해"
    from app.models.agenda import MoodLog

    entry = MoodLog(date=date.today(), score=score, note=note or None)
    ctx.deps.db.add(entry)
    await ctx.deps.db.flush()
    await ctx.deps.db.commit()
    return f"기분 기록했어: {score}점"


async def log_sleep(
    ctx: RunContext[QuarkDeps],
    hours: float,
    quality: int = 3,
) -> str:
    """어젯밤 수면을 기록한다.

    Args:
        hours: 수면 시간 (예: 7.5).
        quality: 수면 질 1-5 (1=매우나쁨, 5=매우좋음).
    """
    if ctx.deps.db is None:
        return "수면 저장 불가 (DB 연결 없음)"
    if not 1 <= quality <= 5:
        return "quality는 1-5 사이여야 해"
    from app.models.agenda import SleepLog

    entry = SleepLog(date=date.today(), hours=hours, quality=quality)
    ctx.deps.db.add(entry)
    await ctx.deps.db.flush()
    await ctx.deps.db.commit()
    return f"수면 기록했어: {hours}시간, 질 {quality}점"


async def log_caffeine(
    ctx: RunContext[QuarkDeps],
    cups: int = 1,
) -> str:
    """오늘 마신 커피를 기록한다 (1잔 = 100mg).

    Args:
        cups: 커피 잔 수 (기본 1).
    """
    if ctx.deps.db is None:
        return "카페인 저장 불가 (DB 연결 없음)"
    from app.models.agenda import CaffeineLog

    for _ in range(cups):
        entry = CaffeineLog(date=date.today(), amount_mg=100)
        ctx.deps.db.add(entry)
    await ctx.deps.db.flush()
    await ctx.deps.db.commit()
    return f"카페인 기록했어: {cups}잔 ({cups * 100}mg)"


ASSISTANT_TOOLS = (
    add_event,
    list_events,
    update_event,
    cancel_event,
    add_todo,
    complete_todo,
    add_idea,
    add_habit,
    list_habits,
    web_search,
    get_weather,
    log_mood,
    log_sleep,
    log_caffeine,
)


def register_assistant_tools(agent: Agent[QuarkDeps, str]) -> None:
    """Register every assistant tool on the given agent."""
    for tool in ASSISTANT_TOOLS:
        agent.tool(tool)
