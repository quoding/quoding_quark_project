from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, Sequence
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from app.agents.deps import QuarkDeps
from app.agents.quark_agent import quark_agent
from app.core.redis import get_redis
from app.services.memory import redis_append_conversation, redis_get_conversation
from app.services.mqtt_bridge import mqtt_bridge

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str


def _to_message_history(turns: list[dict[str, str]]) -> list[ModelMessage]:
    """Convert stored Redis turns into Pydantic AI message history."""
    history: list[ModelMessage] = []
    for turn in turns:
        content = turn.get("content", "")
        if turn.get("role") == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        else:
            history.append(ModelResponse(parts=[TextPart(content=content)]))
    return history


def _sse(data: dict[str, object]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_agent(
    redis: aioredis.Redis,
    session_id: str,
    message: str,
    history: Sequence[ModelMessage],
) -> AsyncGenerator[str, None]:
    """Stream the agent's real token deltas, then persist the assistant turn."""
    deps = QuarkDeps(mqtt=mqtt_bridge, redis=redis)
    chunks: list[str] = []
    async with quark_agent.run_stream(
        message, message_history=list(history), deps=deps
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
) -> StreamingResponse:
    turns = await redis_get_conversation(redis, req.session_id)
    history = _to_message_history(turns)
    await redis_append_conversation(redis, req.session_id, "user", req.message)

    return StreamingResponse(
        _stream_agent(redis, req.session_id, req.message, history),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
