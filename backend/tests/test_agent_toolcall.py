"""Core integration test (COMPLETION CONDITION 10).

"거실 불 꺼줘" → agent calls ``toggle_light`` → ``mqtt_bridge.publish`` emits
``quark/cmd/light/living`` with ``{"value": false}``. Tool-call is forced with a
``FunctionModel`` so no live LLM is involved.
"""
from __future__ import annotations

from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.agents.deps import QuarkDeps
from app.agents.quark_agent import quark_agent
from app.services.mqtt_bridge import MqttBridge


def _toggle_then_reply(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    # If the conversation already contains the tool's return, answer in text.
    for message in messages:
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                return ModelResponse(parts=[TextPart(content="오케이, 거실 불 껐어 💡")])
    # Otherwise, force the toggle_light tool call.
    return ModelResponse(
        parts=[ToolCallPart(tool_name="toggle_light", args={"room": "living", "on": False})]
    )


async def test_living_light_off_triggers_mqtt(mock_bridge: MqttBridge) -> None:
    deps = QuarkDeps(mqtt=mock_bridge)
    with quark_agent.override(model=FunctionModel(_toggle_then_reply)):
        result = await quark_agent.run("거실 불 꺼줘", deps=deps)

    mock_bridge.publish.assert_awaited_once_with(  # type: ignore[attr-defined]
        "quark/cmd/light/living", {"value": False}
    )
    assert "거실" in result.output
