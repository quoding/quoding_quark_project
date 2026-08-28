from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from app.services.mqtt_bridge import MqttMessage, mqtt_bridge

logger = logging.getLogger(__name__)

_ALERT_COOLDOWN = 6 * 3600.0  # 같은 토픽 알림 최소 간격 (초)


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

        # Low moisture → Discord 알림 (토픽별 쿨다운으로 센서 주기 발행 스팸 방지)
        last_alert: dict[str, float] = {}

        async def _low_moisture_alert(msg: MqttMessage) -> None:
            from app.core.database import AsyncSessionLocal
            from app.services.automation_gate import is_enabled, mark_run

            try:
                async with AsyncSessionLocal() as db:
                    enabled = await is_enabled(db, "plant-watering")
            except Exception:
                logger.warning("Automation gate check failed for plant-watering, running anyway", exc_info=True)
                enabled = True
            if not enabled:
                logger.info("Automation 'plant-watering' is disabled, skipping")
                return

            val = msg.payload.get("value", 100) if isinstance(msg.payload, dict) else 100
            logger.warning("Low moisture on %s: %s%%", msg.topic, val)

            now = time.monotonic()
            if now - last_alert.get(msg.topic, -_ALERT_COOLDOWN) < _ALERT_COOLDOWN:
                return
            last_alert[msg.topic] = now

            from app.services.notify import notify

            parts = msg.topic.split("/")
            device = parts[2] if len(parts) > 2 else msg.topic
            await notify(f"🌱 {device} 토양 수분이 {val}%야 — 물 줄 때 됐어!")

            try:
                async with AsyncSessionLocal() as db:
                    await mark_run(db, "plant-watering")
            except Exception:
                logger.warning("Failed to mark automation run for plant-watering", exc_info=True)

        self.register(
            Rule(
                name="low-moisture-alert",
                topic_pattern="quark/sensor/+/moisture",
                condition=lambda p: isinstance(p, dict) and p.get("value", 100) < 30,
                action=_low_moisture_alert,
            )
        )


rule_router = RuleRouter()
