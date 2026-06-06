"""Personal-assistant function tools for the QUARK agent.

These tools access the database (scheduled_events, todos, ideas) and perform
web searches. They require ctx.deps.db to be non-None for DB operations.
"""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime
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
    tag: str = "개인",
) -> str:
    """일정을 DB에 저장한다.

    Args:
        title: 일정 제목.
        scheduled_at: ISO 8601 형식 날짜시간 (예: 2026-06-10T14:00:00).
        tag: 태그 — 회의 | 마감 | 작업 | 개인.
    """
    if ctx.deps.db is None:
        return "일정 저장 불가 (DB 연결 없음)"
    from app.models.agenda import ScheduledEvent

    try:
        dt = datetime.fromisoformat(scheduled_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        ev = ScheduledEvent(title=title, scheduled_at=dt, tag=tag)
        ctx.deps.db.add(ev)
        await ctx.deps.db.flush()
        await ctx.deps.db.commit()
        return f"일정 저장했어: {title} ({scheduled_at})"
    except ValueError as exc:
        return f"날짜 형식 오류: {exc}"


async def list_events(
    ctx: RunContext[QuarkDeps],
    target_date: str | None = None,
) -> str:
    """일정 목록을 반환한다.

    Args:
        target_date: 조회할 날짜 (YYYY-MM-DD). 생략 시 오늘.
    """
    if ctx.deps.db is None:
        return "일정 조회 불가 (DB 연결 없음)"
    from app.models.agenda import ScheduledEvent

    try:
        if target_date:
            d = date.fromisoformat(target_date)
        else:
            d = date.today()

        day_start = datetime(d.year, d.month, d.day, tzinfo=UTC)
        day_end = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=UTC)
        result = await ctx.deps.db.execute(
            select(ScheduledEvent)
            .where(ScheduledEvent.scheduled_at >= day_start)
            .where(ScheduledEvent.scheduled_at <= day_end)
            .order_by(ScheduledEvent.scheduled_at)
        )
        events = result.scalars().all()
        if not events:
            return f"{d.isoformat()} 일정 없음"
        lines = [f"- {e.scheduled_at.strftime('%H:%M')} {e.title} [{e.tag}]" for e in events]
        return f"{d.isoformat()} 일정:\n" + "\n".join(lines)
    except ValueError as exc:
        return f"날짜 형식 오류: {exc}"


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


ASSISTANT_TOOLS = (
    add_event,
    list_events,
    add_todo,
    complete_todo,
    add_idea,
    add_habit,
    list_habits,
    web_search,
)


def register_assistant_tools(agent: Agent[QuarkDeps, str]) -> None:
    """Register every assistant tool on the given agent."""
    for tool in ASSISTANT_TOOLS:
        agent.tool(tool)
