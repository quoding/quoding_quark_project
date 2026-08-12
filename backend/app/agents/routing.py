"""Model routing: select nano (default) vs mini (complex) based on message heuristics.

Rules:
- Model IDs come exclusively from config, never hardcoded.
- Tests cover: short/simple → nano, long/complex → mini.
"""
from __future__ import annotations

from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core.config import get_settings

settings = get_settings()

_COMPLEX_MARKERS: tuple[str, ...] = (
    "분석",
    "비교",
    "요약해줘",
    "설명해줘",
    "왜",
    "어떻게",
    "explain",
    "analyze",
    "compare",
    "summarize",
)

_COMPLEX_THRESHOLD_CHARS = 200
_COMPLEX_MARKER_HITS = 2


def select_model_id(message: str) -> str:
    """Return the model ID appropriate for *message* complexity/length."""
    if len(message) > _COMPLEX_THRESHOLD_CHARS:
        return settings.openai_model_complex
    hits = sum(1 for marker in _COMPLEX_MARKERS if marker in message)
    if hits >= _COMPLEX_MARKER_HITS:
        return settings.openai_model_complex
    return settings.openai_model_default


def build_model(message: str) -> OpenAIResponsesModel:
    """Return an ``OpenAIResponsesModel`` sized for *message* complexity.

    Uses the Responses API rather than Chat Completions: models like
    gpt-5.6-luna reject function-tool calls combined with reasoning_effort
    on /v1/chat/completions, and quark_agent's tools rely on both.

    ``agent.override(model=TestModel())`` always takes priority over this in tests.
    """
    model_id = select_model_id(message)
    provider = OpenAIProvider(api_key=settings.openai_api_key or "sk-no-key-configured")
    return OpenAIResponsesModel(model_id, provider=provider)
