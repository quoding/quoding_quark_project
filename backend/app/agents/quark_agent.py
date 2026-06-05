"""QUARK — the personal maker assistant agent (Pydantic AI).

The agent is importable and testable without a live OpenAI key: the model is
constructed with a placeholder key (no network call happens at import time) and
tests inject ``TestModel`` / ``FunctionModel`` via ``quark_agent.override(...)``.
The real key is only ever read from ``settings.openai_api_key`` (Docker secret).
"""
from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.deps import QuarkDeps
from app.core.config import get_settings
from app.tools.home import register_home_tools

settings = get_settings()

SYSTEM_PROMPT = """\
너는 '쿼크(QUARK)' — 쿼딩의 개인 비서야. 1인 메이커이자 유튜버인 그를 돕는다.

말투:
- 친근한 반말, 짧고 명확하게. 과장된 존댓말 금지.
- 한국어로 답한다. 필요하면 이모지 1개 정도로 가볍게.
- 메이커 감성(하드웨어·홈랩·LED·식물·서버)을 이해하고 거든다.

행동:
- 일상 대화와 일반 질문(상식·인물·코딩·아이디어 등)에는 그냥 평범하게, 아는 만큼 제대로 답해.
  모든 말을 '작업 접수'로 받아들이지 마 — "접수했어 / 곧 처리할게" 같은 말은 진짜 기기 제어나
  작업을 실제로 실행할 때만 써. 질문엔 답을, 잡담엔 잡담을.
- 집 안 기기 제어 요청일 때만 적절한 툴을 호출해 실제로 실행해. 추측해서 끄지 말고,
  애매하면 어떤 기기인지 한 번 되물어.
- 조명 위치는 living(거실)/bed(침실)/desk(책상)/kitchen(주방).
- 씬은 focus(집중)/sleep(취침)/film(영상촬영)/home(귀가)/relax(휴식).
- 툴 실행 후에는 무엇을 했는지 한 줄로 자연스럽게 확인해 줘.
- 모르는 건 모른다고 솔직하게.
"""


def _build_model() -> OpenAIChatModel:
    """Construct the default chat model from config.

    Uses ``settings.openai_model_default`` (``gpt-5.4-nano``) — never hardcoded.
    A placeholder key keeps construction offline-safe; the live key is used only
    when an actual request is made in production.
    """
    provider = OpenAIProvider(api_key=settings.openai_api_key or "sk-no-key-configured")
    return OpenAIChatModel(settings.openai_model_default, provider=provider)


quark_agent: Agent[QuarkDeps, str] = Agent(
    _build_model(),
    deps_type=QuarkDeps,
    output_type=str,
    system_prompt=SYSTEM_PROMPT,
)

register_home_tools(quark_agent)
