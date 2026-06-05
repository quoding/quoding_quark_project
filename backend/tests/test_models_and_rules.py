"""Model metadata, agent import-without-key, and the fast-path rule router."""
from __future__ import annotations

from app.core.config import get_settings
from app.core.database import Base
from app.services.mqtt_bridge import MqttMessage
from app.services.rule_router import RuleRouter


def test_all_tables_registered() -> None:
    tables = set(Base.metadata.tables)
    assert {"devices", "agent_memories", "daily_episodes", "automations"} <= tables


def test_agent_memories_column_name() -> None:
    # Raw SQL in services/memory.py targets a literal ``metadata`` column.
    cols = {c.name for c in Base.metadata.tables["agent_memories"].columns}
    assert "metadata" in cols
    assert "embedding" in cols


def test_agent_importable_without_live_key() -> None:
    # No live OpenAI key in the test environment.
    assert get_settings().openai_api_key == ""
    from app.agents.quark_agent import quark_agent

    assert quark_agent is not None


async def test_rule_router_low_moisture_triggers() -> None:
    router = RuleRouter()
    fired: list[str] = []

    async def _action(msg: MqttMessage) -> None:
        fired.append(msg.topic)

    from app.services.rule_router import Rule

    router.register(
        Rule(
            name="t",
            topic_pattern="quark/sensor/+/moisture",
            condition=lambda p: isinstance(p, dict) and p.get("value", 100) < 30,
            action=_action,
        )
    )
    await router._handle(MqttMessage(topic="quark/sensor/plant-01/moisture", payload={"value": 12}))
    assert fired == ["quark/sensor/plant-01/moisture"]
