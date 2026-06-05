from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import redis.asyncio as aioredis

from app.core.redis import get_redis
from app.services.memory import redis_append_conversation, redis_get_conversation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str


async def _stream_chat(session_id: str, user_msg: str, history: list[dict]) -> AsyncGenerator[str, None]:
    """Placeholder SSE stream — replace with actual Pydantic AI agent call."""
    yield f"data: {json.dumps({'role': 'assistant', 'delta': 'QUARK: '})}\n\n"
    response = f"Received: {user_msg}"
    for char in response:
        yield f"data: {json.dumps({'delta': char})}\n\n"
        await asyncio.sleep(0.02)
    yield f"data: {json.dumps({'done': True})}\n\n"


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> StreamingResponse:
    history = await redis_get_conversation(redis, req.session_id)
    await redis_append_conversation(redis, req.session_id, "user", req.message)

    return StreamingResponse(
        _stream_chat(req.session_id, req.message, history),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
