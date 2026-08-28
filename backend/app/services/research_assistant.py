"""Arxiv 연구조수 — LangGraph 학습용 파이프라인 (fetch → rank → filter → summarize → save).

`quark_agent`(단일 채팅 에이전트, CLAUDE.md)와는 분리된 독립 배치 워크플로우.
수동 트리거 전용 — 자동 스케줄러 job으로 등록하지 않는다 (LLM 호출 비용/빈도 고려,
사용자 요청).

Arxiv API 자체는 인용수 개념이 없어서(단순 논문 저장소), 최신순으로만 가져오면
품질이 들쭉날쭉하다 — 그래서 관련도(relevance) 기준으로 넓게 후보를 모은 뒤
Semantic Scholar(무료, 키 불필요)에서 실제 인용수를 붙여 인용순으로 상위
max_results개만 추린다.
"""
from __future__ import annotations

import logging
import re
from typing import Any, TypedDict

import httpx
from langgraph.graph import END, StateGraph
from sqlalchemy import select

from app.core.config import get_settings
from app.services.notify import notify

logger = logging.getLogger(__name__)

_ARXIV_API = "https://export.arxiv.org/api/query"
_S2_BATCH_API = "https://api.semanticscholar.org/graph/v1/paper/batch"
_POOL_MULTIPLIER = 4  # 후보를 max_results보다 넉넉히 모아서 인용순으로 추린다


class ResearchState(TypedDict):
    keyword: str
    max_results: int
    papers: list[dict[str, Any]]
    new_papers: list[dict[str, Any]]
    saved: list[dict[str, Any]]


async def _fetch_arxiv(keyword: str, pool_size: int) -> list[dict[str, Any]]:
    query = " AND ".join(f"all:{w}" for w in keyword.split())
    params = {
        "search_query": query,
        "sortBy": "relevance",
        "sortOrder": "descending",
        "max_results": str(pool_size),
    }
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(_ARXIV_API, params=params)
            resp.raise_for_status()
            text = resp.text
    except Exception:
        logger.warning("Arxiv fetch failed for keyword=%r", keyword, exc_info=True)
        return []

    import feedparser  # type: ignore[import-untyped]

    feed = feedparser.parse(text)
    papers: list[dict[str, Any]] = []
    for entry in feed.entries:
        raw_id = entry.get("id", "")
        arxiv_id = raw_id.rsplit("/", 1)[-1] if raw_id else ""
        if not arxiv_id:
            continue
        papers.append(
            {
                "arxiv_id": arxiv_id,
                "title": " ".join(entry.get("title", "").split()),
                "authors": ", ".join(a.get("name", "") for a in entry.get("authors", [])),
                "abstract": " ".join(entry.get("summary", "").split()),
                "url": raw_id,
                "citation_count": 0,
            }
        )
    return papers


async def _fetch_citation_counts(arxiv_ids: list[str]) -> dict[str, int]:
    """Semantic Scholar 배치 조회 — 실패하거나 못 찾으면 0으로 취급 (파이프라인은 계속 진행)."""
    if not arxiv_ids:
        return {}

    bare_ids = {aid: re.sub(r"v\d+$", "", aid) for aid in arxiv_ids}
    payload = {"ids": [f"ARXIV:{bare}" for bare in bare_ids.values()]}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(_S2_BATCH_API, params={"fields": "citationCount"}, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.warning("Semantic Scholar citation lookup failed", exc_info=True)
        return {}

    counts: dict[str, int] = {}
    for arxiv_id, entry in zip(arxiv_ids, data):
        if isinstance(entry, dict):
            counts[arxiv_id] = int(entry.get("citationCount") or 0)
    return counts


async def _fetch_node(state: ResearchState) -> dict[str, Any]:
    pool_size = max(state["max_results"] * _POOL_MULTIPLIER, 10)
    papers = await _fetch_arxiv(state["keyword"], pool_size)
    return {"papers": papers}


async def _rank_node(state: ResearchState) -> dict[str, Any]:
    """인용수로 보강한 뒤 인용순 정렬, 상위 max_results개만 남긴다."""
    papers = state["papers"]
    if not papers:
        return {"papers": []}

    counts = await _fetch_citation_counts([p["arxiv_id"] for p in papers])
    for p in papers:
        p["citation_count"] = counts.get(p["arxiv_id"], 0)

    ranked = sorted(papers, key=lambda p: p["citation_count"], reverse=True)
    return {"papers": ranked[: state["max_results"]]}


async def _filter_node(state: ResearchState) -> dict[str, Any]:
    ids = [p["arxiv_id"] for p in state["papers"]]
    if not ids:
        return {"new_papers": []}

    from app.core.database import AsyncSessionLocal
    from app.models.research import ResearchNote

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(ResearchNote.arxiv_id).where(ResearchNote.arxiv_id.in_(ids)))
        existing = {row[0] for row in res.all()}

    new_papers = [p for p in state["papers"] if p["arxiv_id"] not in existing]
    return {"new_papers": new_papers}


async def _summarize_node(state: ResearchState) -> dict[str, Any]:
    if not state["new_papers"]:
        return {"new_papers": []}

    from openai import AsyncOpenAI

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    summarized: list[dict[str, Any]] = []
    for p in state["new_papers"]:
        prompt = (
            "다음 논문 초록을 한국어로 3문장 이내로 핵심만 요약해줘 (군더더기 설명 없이 요약문만).\n\n"
            f"제목: {p['title']}\n초록: {p['abstract']}"
        )
        try:
            resp = await client.chat.completions.create(
                model=settings.openai_model_default,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=300,
            )
            summary_ko = (resp.choices[0].message.content or "").strip()
        except Exception:
            logger.warning("Research summarize failed for %s", p["arxiv_id"], exc_info=True)
            summary_ko = p["abstract"][:200]
        summarized.append({**p, "summary_ko": summary_ko})

    return {"new_papers": summarized}


async def _save_node(state: ResearchState) -> dict[str, Any]:
    from app.core.database import AsyncSessionLocal
    from app.models.research import ResearchNote

    saved: list[dict[str, Any]] = []
    async with AsyncSessionLocal() as db:
        for p in state["new_papers"]:
            note = ResearchNote(
                arxiv_id=p["arxiv_id"],
                title=p["title"],
                authors=p["authors"],
                summary_ko=p["summary_ko"],
                url=p["url"],
                keyword=state["keyword"],
                citation_count=p.get("citation_count", 0),
            )
            db.add(note)
            saved.append(p)
        await db.commit()

    if saved:
        lines = [f"- {p['title']} (인용 {p.get('citation_count', 0)}회)" for p in saved]
        msg = f"📚 새 논문 {len(saved)}건 저장했어 (키워드: {state['keyword']}):\n" + "\n".join(lines)
        await notify(msg)

    return {"saved": saved}


def _build_graph() -> Any:
    graph = StateGraph(ResearchState)
    graph.add_node("fetch", _fetch_node)
    graph.add_node("rank", _rank_node)
    graph.add_node("filter", _filter_node)
    graph.add_node("summarize", _summarize_node)
    graph.add_node("save", _save_node)
    graph.set_entry_point("fetch")
    graph.add_edge("fetch", "rank")
    graph.add_edge("rank", "filter")
    graph.add_edge("filter", "summarize")
    graph.add_edge("summarize", "save")
    graph.add_edge("save", END)
    return graph.compile()


_graph = _build_graph()


async def run_research_pipeline(keyword: str | None = None, max_results: int = 5) -> dict[str, Any]:
    """수동 트리거 — 지정 키워드(또는 설정 기본 키워드 전체)로 Arxiv 조사·인용순 정렬·요약·저장."""
    settings = get_settings()
    keywords = [keyword] if keyword else [k.strip() for k in settings.research_keywords.split(",") if k.strip()]

    total_fetched = 0
    total_saved: list[dict[str, Any]] = []
    for kw in keywords:
        result = await _graph.ainvoke(
            {"keyword": kw, "max_results": max_results, "papers": [], "new_papers": [], "saved": []}
        )
        total_fetched += len(result.get("papers", []))
        total_saved.extend(result.get("saved", []))

    return {"keywords": keywords, "fetched": total_fetched, "saved": len(total_saved), "papers": total_saved}
