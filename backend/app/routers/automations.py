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

# 기본 자동화 규칙 (APScheduler 잡 + MQTT 트리거 대응)
_DEFAULTS = [
    {"name": "아침 브리핑", "trigger_desc": "매일 08:00", "action_desc": "날씨·일정·할일 요약 → Discord 전송", "icon": "sun"},
    {"name": "주간 리뷰", "trigger_desc": "금요일 17:00", "action_desc": "주간 완료 항목·습관 스트릭 요약 → Discord", "icon": "check"},
    {"name": "커밋 리마인더", "trigger_desc": "매일 23:00", "action_desc": "오늘 커밋 없으면 Discord 알림", "icon": "automation"},
    {"name": "습관 초기화", "trigger_desc": "매일 00:01", "action_desc": "모든 습관 done_today → false 리셋", "icon": "reset"},
    {"name": "취침 모드", "trigger_desc": "조명 전체 꺼짐 감지", "action_desc": "에어컨 26° 설정 + LED 끄기", "icon": "bed"},
    {"name": "식물 급수", "trigger_desc": "토양 습도 < 40%", "action_desc": "MQTT 급수 명령 전송", "icon": "leaf"},
]


class AutomationOut(BaseModel):
    id: int
    name: str
    trigger_desc: str
    action_desc: str
    icon: str
    enabled: bool
    run_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AutomationCreate(BaseModel):
    name: str
    trigger_desc: str
    action_desc: str
    icon: str = "zap"


async def seed_defaults(db: AsyncSession) -> None:
    result = await db.execute(select(Automation).limit(1))
    if result.scalar_one_or_none() is not None:
        return
    for d in _DEFAULTS:
        db.add(Automation(**d))
    await db.commit()


@router.get("", response_model=list[AutomationOut])
async def list_automations(db: AsyncSession = Depends(get_db)) -> list[Automation]:
    await seed_defaults(db)
    result = await db.execute(select(Automation).order_by(Automation.created_at))
    return list(result.scalars().all())


@router.post("", response_model=AutomationOut, status_code=201)
async def create_automation(body: AutomationCreate, db: AsyncSession = Depends(get_db)) -> Automation:
    auto = Automation(name=body.name, trigger_desc=body.trigger_desc, action_desc=body.action_desc, icon=body.icon)
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
    await db.delete(auto)
    await db.commit()
    return Response(status_code=204)
