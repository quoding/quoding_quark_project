from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ResearchNote(Base):
    """Arxiv 연구조수 파이프라인(LangGraph)이 저장하는 논문 요약 아카이브."""

    __tablename__ = "research_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    arxiv_id: Mapped[str] = mapped_column(Text, unique=True, index=True)
    title: Mapped[str] = mapped_column(Text)
    authors: Mapped[str] = mapped_column(Text)
    summary_ko: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    keyword: Mapped[str] = mapped_column(Text)
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
