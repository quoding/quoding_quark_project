from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agenda import Automation

router = APIRouter(prefix="/automations", tags=["automations"])

# 고정 자동화 — slug로 실제 실행 코드(scheduler.py 크론 job / rule_router.py MQTT 규칙)와
# 연결됨. 여기 없는 slug를 실행 코드에서 체크하면 automation_gate.is_enabled()가
# fail-open으로 True를 반환하므로, 새 고정 자동화를 추가할 땐 반드시 여기도 같이 추가할 것.
# "취침 모드"는 대응하는 실행 코드가 아직 없어서 시딩에서 제외 — 실제로 만들 때 추가.
_DEFAULTS = [
    {"name": "아침 브리핑", "trigger_desc": "매일 08:00", "action_desc": "날씨·일정·할일 요약 → Discord 전송", "icon": "sun", "kind": "cron", "slug": "morning-brief"},
    {"name": "주간 리뷰", "trigger_desc": "금요일 17:00", "action_desc": "주간 완료 항목·습관 스트릭 요약 → Discord", "icon": "check", "kind": "cron", "slug": "weekly-review"},
    {"name": "커밋 리마인더", "trigger_desc": "매일 23:00", "action_desc": "오늘 커밋 없으면 Discord 알림", "icon": "automation", "kind": "cron", "slug": "commit-reminder"},
    {"name": "습관 초기화", "trigger_desc": "매일 00:01", "action_desc": "모든 습관 done_today → false 리셋", "icon": "reset", "kind": "cron", "slug": "habit-daily-reset"},
    {"name": "식물 급수 알림", "trigger_desc": "토양 습도 < 30%", "action_desc": "Discord로 급수 필요 알림 전송", "icon": "leaf", "kind": "mqtt_rule", "slug": "plant-watering"},
]


class AutomationOut(BaseModel):
    id: int
    name: str
    trigger_desc: str
    action_desc: str
    icon: str
    enabled: bool
    run_count: int
    kind: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AutomationCreate(BaseModel):
    name: str
    trigger_desc: str
    action_desc: str
    icon: str = "zap"


async def seed_defaults(db: AsyncSession) -> None:
    """slug별 idempotent upsert — 이미 있는 행의 enabled 값은 절대 건드리지 않는다."""
    result = await db.execute(select(Automation.slug).where(Automation.slug.is_not(None)))
    existing_slugs = {row for row in result.scalars().all()}
    added = False
    for d in _DEFAULTS:
        if d["slug"] in existing_slugs:
            continue
        db.add(Automation(**d))
        added = True
    if added:
        await db.commit()


@router.get("", response_model=list[AutomationOut])
async def list_automations(db: AsyncSession = Depends(get_db)) -> list[Automation]:
    await seed_defaults(db)
    result = await db.execute(select(Automation).order_by(Automation.created_at))
    return list(result.scalars().all())


@router.post("", response_model=AutomationOut, status_code=201)
async def create_automation(body: AutomationCreate, db: AsyncSession = Depends(get_db)) -> Automation:
    auto = Automation(name=body.name, trigger_desc=body.trigger_desc, action_desc=body.action_desc, icon=body.icon, kind="macro")
    db.add(auto)
    await db.flush()
    await db.commit()
    await db.refresh(auto)
    return auto


@router.patch("/{auto_id}/toggle", response_model=AutomationOut)
async def toggle_automation(auto_id: int, db: AsyncSession = Depends(get_db)) -> Automation:
    result = await db.execute(select(Automation).where(Automation.id == auto_id))
    auto = result.scalar_one_or_none()
    if auto is None:
        raise HTTPException(status_code=404, detail="Automation not found")
    auto.enabled = not auto.enabled
    await db.flush()
    await db.commit()
    await db.refresh(auto)
    return auto


@router.delete("/{auto_id}", status_code=204, response_class=Response)
async def delete_automation(auto_id: int, db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(select(Automation).where(Automation.id == auto_id))
    auto = result.scalar_one_or_none()
    if auto is None:
        raise HTTPException(status_code=404, detail="Automation not found")
    if auto.kind != "macro":
        raise HTTPException(status_code=409, detail="시스템 자동화는 삭제할 수 없습니다. 껐다 켜는 것만 가능합니다.")
    await db.delete(auto)
    await db.commit()
    return Response(status_code=204)
