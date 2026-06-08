from __future__ import annotations

import re
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.deps import QuarkDeps
from app.agents.quark_agent import quark_agent
from app.agents.routing import build_model
from app.core.auth import verify_siri_token
from app.core.database import get_db_optional
from app.core.redis import get_redis
from app.services.memory import redis_append_conversation, redis_get_conversation, to_message_history
from app.services.mqtt_bridge import mqtt_bridge

router = APIRouter(prefix="/siri", tags=["siri"], dependencies=[Depends(verify_siri_token)])

# Siri 호출은 단축어가 session_id를 들고 다니지 않으므로, 고정 세션으로 묶어
# "Hey Siri, 퀀크한테 물어봐"를 연달아 사용할 때 직전 대화 맥락이 이어지게 한다.
# (Redis TTL — settings.redis_ttl_seconds, 기본 24h — 가 지나면 자연히 새 대화로 시작됨)
_DEFAULT_SESSION_ID = "siri-default"


class SiriAskRequest(BaseModel):
    message: str
    session_id: str | None = None


class SiriAskResponse(BaseModel):
    reply: str


_MARKDOWN_HEADER_RE = re.compile(r"^#+\s*", flags=re.MULTILINE)
_MARKDOWN_CHAR_RE = re.compile(r"[*_`~]")
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # symbols, pictographs, emoticons, transport, supplemental
    "\U00002600-\U000027BF"  # misc symbols & dingbats
    "\U0001F1E6-\U0001F1FF"  # regional indicator (flags)
    "\U00002B00-\U00002BFF"  # misc symbols & arrows
    "️‍"  # variation selector / zero-width joiner
    "]+"
)
_BLANK_RUN_RE = re.compile(r"[ \t]{2,}")


def _clean_for_speech(text: str) -> str:
    """Siri TTS가 마크다운 강조 기호("**굵게**")나 이모지를 그대로 읽지 않도록 정리한다."""
    text = _MARKDOWN_HEADER_RE.sub("", text)
    text = _MARKDOWN_CHAR_RE.sub("", text)
    text = _EMOJI_RE.sub("", text)
    return _BLANK_RUN_RE.sub(" ", text).strip()


@router.post("/ask")
async def siri_ask(
    req: SiriAskRequest,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    db: Annotated[AsyncSession | None, Depends(get_db_optional)],
) -> SiriAskResponse:
    """음성 질의를 받아 quark_agent를 동기 실행하고, TTS용으로 정리한 답변을 반환한다 (Siri Shortcuts용).

    session_id를 생략하면 고정 세션(_DEFAULT_SESSION_ID)으로 대화를 이어가고,
    값을 넘기면 그 세션으로 대화 맥락을 분리해 관리한다.
    """
    session_id = req.session_id or _DEFAULT_SESSION_ID
    turns = await redis_get_conversation(redis, session_id)
    history = to_message_history(turns)

    deps = QuarkDeps(mqtt=mqtt_bridge, redis=redis, db=db)
    result = await quark_agent.run(
        req.message, message_history=history, deps=deps, model=build_model(req.message)
    )

    await redis_append_conversation(redis, session_id, "user", req.message)
    await redis_append_conversation(redis, session_id, "assistant", result.output)
    return SiriAskResponse(reply=_clean_for_speech(result.output))
