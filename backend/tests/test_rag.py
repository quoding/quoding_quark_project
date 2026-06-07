"""RAG service: save_memory, retrieve, create_daily_summary, remember_fact tool."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fakeredis import aioredis as fake_aioredis
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.quark_agent import quark_agent
from app.services.memory import redis_append_conversation
from app.services.rag import create_daily_summary, retrieve, save_memory

_FAKE_EMBEDDING = [0.1] * 1536


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture(autouse=True)
def _embedding_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """기본적으로 임베딩 토글이 켜진 것으로 가정 — Redis 실호출 방지."""
    monkeypatch.setattr("app.services.rag.is_embedding_enabled", AsyncMock(return_value=True))


# ── save_memory ──────────────────────────────────────────────────────────────


async def test_save_memory_embeds_and_inserts(mock_db: AsyncMock) -> None:
    with patch("app.services.rag.get_embedding", return_value=_FAKE_EMBEDDING):
        await save_memory("테스트 기억", {"source": "test"}, mock_db)

    mock_db.add.assert_called_once()
    added: Any = mock_db.add.call_args[0][0]
    assert added.content == "테스트 기억"
    assert added.embedding == _FAKE_EMBEDDING
    mock_db.commit.assert_awaited_once()


# ── retrieve ─────────────────────────────────────────────────────────────────


async def test_retrieve_returns_pgvector_results(mock_db: AsyncMock) -> None:
    fake_results: list[dict[str, Any]] = [
        {"content": "과거 기억", "metadata": {}, "similarity": 0.9}
    ]
    with (
        patch("app.services.rag.get_embedding", return_value=_FAKE_EMBEDDING),
        patch("app.services.rag.pgvector_search", return_value=fake_results),
    ):
        results = await retrieve("쿼리", mock_db, k=1)

    assert results == fake_results


async def test_retrieve_results_contain_expected_content(mock_db: AsyncMock) -> None:
    fake_results: list[dict[str, Any]] = [
        {"content": "LED 색상 선호도: 파란색", "metadata": {}, "similarity": 0.85}
    ]
    with (
        patch("app.services.rag.get_embedding", return_value=_FAKE_EMBEDDING),
        patch("app.services.rag.pgvector_search", return_value=fake_results),
    ):
        results = await retrieve("LED 색 뭐가 좋아?", mock_db, k=3)

    assert any("LED" in r["content"] for r in results)


# ── create_daily_summary ─────────────────────────────────────────────────────


async def test_create_daily_summary_calls_save(
    fake_redis: fake_aioredis.FakeRedis,
    mock_db: AsyncMock,
) -> None:
    await redis_append_conversation(fake_redis, "sum-session", "user", "안녕 쿼크")
    await redis_append_conversation(fake_redis, "sum-session", "assistant", "응, 안녕!")

    with (
        quark_agent.override(model=TestModel(call_tools=[])),
        patch("app.services.rag.save_daily_summary") as save_mock,
    ):
        await create_daily_summary("sum-session", fake_redis, mock_db)

    save_mock.assert_awaited_once()
    saved_dict: Any = save_mock.await_args[0][1]
    assert "text" in saved_dict


async def test_create_daily_summary_skips_empty_session(
    fake_redis: fake_aioredis.FakeRedis,
    mock_db: AsyncMock,
) -> None:
    with patch("app.services.rag.save_daily_summary") as save_mock:
        await create_daily_summary("empty-session", fake_redis, mock_db)
    save_mock.assert_not_awaited()


# ── remember_fact tool ───────────────────────────────────────────────────────


async def test_remember_fact_tool_inserts(
    mock_db: AsyncMock, mock_bridge: Any
) -> None:
    """FunctionModel forces remember_fact tool call → save_memory must insert."""

    def _call_remember(
        messages: list[ModelMessage], info: AgentInfo
    ) -> ModelResponse:
        for msg in messages:
            for part in msg.parts:
                if isinstance(part, ToolReturnPart):
                    return ModelResponse(parts=[TextPart(content="기억했어")])
        return ModelResponse(
            parts=[ToolCallPart(tool_name="remember_fact", args={"fact": "테스트 사실"})]
        )

    from app.agents.deps import QuarkDeps

    with (
        patch("app.services.rag.get_embedding", return_value=_FAKE_EMBEDDING),
        quark_agent.override(model=FunctionModel(_call_remember)),
    ):
        result = await quark_agent.run(
            "기억해줘",
            deps=QuarkDeps(mqtt=mock_bridge, db=mock_db),
        )

    mock_db.add.assert_called_once()
    assert "기억했어" in result.output
