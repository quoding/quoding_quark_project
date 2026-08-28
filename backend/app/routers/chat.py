from __future__ import annotations

import datetime as _dt
import json
import logging
from collections.abc import AsyncGenerator, Sequence
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.deps import QuarkDeps
from app.agents.quark_agent import quark_agent
from app.agents.routing import build_model
from app.core.database import get_db, get_db_optional
from app.core.redis import get_redis
from app.models.chat import ChatConversation, ChatMessage
from app.services.memory import (
    persist_message,
    redis_append_conversation,
    redis_get_conversation,
    to_message_history,
)
from app.services.mqtt_bridge import mqtt_bridge

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatSessionOut(BaseModel):
    session_id: str
    title: str | None
    updated_at: _dt.datetime

    model_config = {"from_attributes": True}


class ChatMessageOut(BaseModel):
    role: str
    content: str
    created_at: _dt.datetime

    model_config = {"from_attributes": True}


async def _persist_quietly(db: AsyncSession | None, session_id: str, role: str, content: str) -> None:
    """Best-effort durable write — never let this break the chat stream itself."""
    if db is None:
        return
    try:
        await persist_message(db, session_id, role, content)
    except Exception:
        logger.warning("Failed to persist chat message for session %s", session_id, exc_info=True)
        try:
            await db.rollback()
        except Exception:
            pass


def _sse(data: dict[str, object]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_agent(
    redis: aioredis.Redis,
    session_id: str,
    message: str,
    history: Sequence[ModelMessage],
    db: AsyncSession | None = None,
) -> AsyncGenerator[str, None]:
    """Stream the agent's real token deltas, then persist the assistant turn."""
    deps = QuarkDeps(mqtt=mqtt_bridge, redis=redis, db=db)

    # RAG: retrieve relevant memories and inject as context
    context_note = ""
    if db is not None:
        try:
            from app.services.rag import retrieve

            memories = await retrieve(message, db, k=3)
            if memories:
                lines = "\n".join(f"- {m['content']}" for m in memories)
                context_note = f"\n\n[관련 기억]\n{lines}"
        except Exception:
            logger.warning("RAG retrieve failed, continuing without context", exc_info=True)
            try:
                await db.rollback()
            except Exception:
                pass

    prompt = message + context_note
    model = build_model(message)

    chunks: list[str] = []
    try:
        async with quark_agent.run_stream(
            prompt, message_history=list(history), deps=deps, model=model
        ) as result:
            async for delta in result.stream_text(delta=True):
                chunks.append(delta)
                yield _sse({"delta": delta})
            if not chunks:
                # Some models (e.g. gpt-5.6-luna) emit an empty final text part
                # right after a tool call, and pydantic-ai's streaming path ends
                # the run there instead of retrying like .run() does — get_output()
                # would just return that same empty string. Continue the graph
                # ourselves: drop the empty trailing response and ask the model to
                # finish, without a new user prompt so no tool gets called twice.
                trimmed_history = result.all_messages()[:-1]
                retry_result = await quark_agent.run(
                    None, message_history=trimmed_history, deps=deps, model=model
                )
                if retry_result.output:
                    chunks.append(retry_result.output)
                    yield _sse({"delta": retry_result.output})
    except Exception:
        logger.exception("Agent stream failed for session %s", session_id)
        yield _sse({"error": "응답 생성에 실패했어. 잠시 후 다시 시도해줘.", "done": True})
        return

    await redis_append_conversation(redis, session_id, "assistant", "".join(chunks))
    await _persist_quietly(db, session_id, "assistant", "".join(chunks))
    yield _sse({"done": True})


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    db: Annotated[AsyncSession | None, Depends(get_db_optional)],
) -> StreamingResponse:
    turns = await redis_get_conversation(redis, req.session_id)
    history = to_message_history(turns)
    await redis_append_conversation(redis, req.session_id, "user", req.message)
    await _persist_quietly(db, req.session_id, "user", req.message)

    return StreamingResponse(
        _stream_agent(redis, req.session_id, req.message, history, db),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(db: Annotated[AsyncSession, Depends(get_db)]) -> list[ChatConversation]:
    result = await db.execute(
        select(ChatConversation)
        .where(ChatConversation.source == "web")
        .order_by(ChatConversation.updated_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
async def get_session_messages(
    session_id: str, db: Annotated[AsyncSession, Depends(get_db)]
) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
    )
    return list(result.scalars().all())


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: Annotated[AsyncSession, Depends(get_db)]) -> Response:
    conversation = await db.get(ChatConversation, session_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conversation)
    return Response(status_code=204)
