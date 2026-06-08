from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, Sequence
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.deps import QuarkDeps
from app.agents.quark_agent import quark_agent
from app.agents.routing import build_model
from app.core.database import get_db_optional
from app.core.redis import get_redis
from app.services.memory import redis_append_conversation, redis_get_conversation, to_message_history
from app.services.mqtt_bridge import mqtt_bridge

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str


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
    async with quark_agent.run_stream(
        prompt, message_history=list(history), deps=deps, model=model
    ) as result:
        async for delta in result.stream_text(delta=True):
            chunks.append(delta)
            yield _sse({"delta": delta})

    await redis_append_conversation(redis, session_id, "assistant", "".join(chunks))
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

    return StreamingResponse(
        _stream_agent(redis, req.session_id, req.message, history, db),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
