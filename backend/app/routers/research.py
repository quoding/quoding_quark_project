"""Arxiv 연구조수 아카이브 — 목록 조회 + 수동 실행 (LangGraph 파이프라인)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.research import ResearchNote

router = APIRouter(prefix="/research", tags=["research"])


class ResearchNoteOut(BaseModel):
    id: int
    arxiv_id: str
    title: str
    authors: str
    summary_ko: str
    url: str
    keyword: str
    citation_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RunRequest(BaseModel):
    keyword: str | None = None
    max_results: int = 5


class RunResult(BaseModel):
    keywords: list[str]
    fetched: int
    saved: int


@router.get("", response_model=list[ResearchNoteOut])
async def list_research_notes(db: AsyncSession = Depends(get_db)) -> list[ResearchNote]:
    res = await db.execute(select(ResearchNote).order_by(ResearchNote.created_at.desc()).limit(100))
    return list(res.scalars().all())


@router.post("/run", response_model=RunResult)
async def run_research(body: RunRequest) -> RunResult:
    from app.services.research_assistant import run_research_pipeline

    result = await run_research_pipeline(keyword=body.keyword, max_results=body.max_results)
    return RunResult(keywords=result["keywords"], fetched=result["fetched"], saved=result["saved"])
