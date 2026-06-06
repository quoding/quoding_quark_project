from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agenda import Idea

router = APIRouter(prefix="/ideas", tags=["ideas"])


class IdeaCreate(BaseModel):
    text: str
    tag: str = "아이디어"


class IdeaOut(BaseModel):
    id: int
    text: str
    tag: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[IdeaOut])
async def list_ideas(db: AsyncSession = Depends(get_db)) -> list[Idea]:
    result = await db.execute(select(Idea).order_by(Idea.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=IdeaOut, status_code=201)
async def create_idea(body: IdeaCreate, db: AsyncSession = Depends(get_db)) -> Idea:
    idea = Idea(text=body.text, tag=body.tag)
    db.add(idea)
    await db.flush()
    await db.refresh(idea)
    return idea
