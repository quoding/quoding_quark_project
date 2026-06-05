from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.services.mqtt_bridge import MqttMessage, mqtt_bridge

logger = logging.getLogger(__name__)


@dataclass
class Rule:
    name: str
    topic_pattern: str
    condition: Any  # callable(payload) -> bool
    action: Any  # async callable(msg) -> None


class RuleRouter:
    """Fast-path rule engine — runs before LLM. O(n) rules per message."""

    def __init__(self) -> None:
        self._rules: list[Rule] = []

    def register(self, rule: Rule) -> None:
        self._rules.append(rule)
        mqtt_bridge.subscribe(rule.topic_pattern, self._handle)

    async def _handle(self, msg: MqttMessage) -> None:
        for rule in self._rules:
            try:
                payload = msg.payload if isinstance(msg.payload, dict) else {}
                if rule.condition(payload):
                    logger.debug("Rule '%s' triggered on %s", rule.name, msg.topic)
                    await rule.action(msg)
            except Exception:
                logger.exception("Rule '%s' error", rule.name)

    def load_defaults(self) -> None:
        """Register built-in rules."""
        from app.services.mqtt_bridge import mqtt_bridge as bridge

        # Example: low moisture → log warning
        async def _low_moisture_alert(msg: MqttMessage) -> None:
            val = msg.payload.get("value", 100) if isinstance(msg.payload, dict) else 100
            if val < 30:
                logger.warning("Low moisture on %s: %s%%", msg.topic, val)

        self.register(
            Rule(
                name="low-moisture-alert",
                topic_pattern="quark/sensor/+/moisture",
                condition=lambda p: isinstance(p, dict) and p.get("value", 100) < 30,
                action=_low_moisture_alert,
            )
        )


rule_router = RuleRouter()
