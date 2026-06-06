"""Model routing: select_model_id heuristics and build_model."""
from __future__ import annotations

from app.agents.routing import build_model, select_model_id
from app.core.config import get_settings

settings = get_settings()


def test_short_simple_message_routes_to_nano() -> None:
    assert select_model_id("안녕") == settings.openai_model_default


def test_long_message_routes_to_mini() -> None:
    long_msg = "이" * 201
    assert select_model_id(long_msg) == settings.openai_model_complex


def test_two_complex_keywords_routes_to_mini() -> None:
    msg = "이 코드를 자세히 분석해줘 왜 느린지 비교해줘"
    assert select_model_id(msg) == settings.openai_model_complex


def test_single_complex_keyword_stays_nano() -> None:
    assert select_model_id("분석해줘") == settings.openai_model_default


def test_build_model_simple_returns_default_model_id() -> None:
    model = build_model("안녕")
    assert str(model.model_name) == settings.openai_model_default


def test_build_model_complex_returns_complex_model_id() -> None:
    model = build_model("이" * 250)
    assert str(model.model_name) == settings.openai_model_complex
