from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import asyncio_mqtt as aiomqtt

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Topic format: quark/{type}/{device-id}/{metric}
# e.g.: quark/sensor/plant-01/moisture, quark/cmd/light-01/power

TOPIC_PREFIX = "quark"


@dataclass
class MqttMessage:
    topic: str
    payload: dict[str, Any] | str
    qos: int = 0


@dataclass
class MqttBridge:
    _client: aiomqtt.Client | None = field(default=None, init=False, repr=False)
    _inbound: asyncio.Queue[MqttMessage] = field(default_factory=asyncio.Queue, init=False)
    _subscribers: dict[str, list[Callable[[MqttMessage], Any]]] = field(
        default_factory=dict, init=False
    )
    _running: bool = field(default=False, init=False)

    async def start(self) -> None:
        self._running = True
        asyncio.create_task(self._run_loop(), name="mqtt-bridge")

    async def stop(self) -> None:
        self._running = False

    async def _run_loop(self) -> None:
        while self._running:
            try:
                async with aiomqtt.Client(
                    hostname=settings.mqtt_host,
                    port=settings.mqtt_port,
                    username=settings.mqtt_user,
                    password=settings.mqtt_password,
                    client_id=settings.mqtt_client_id,
                    keepalive=60,
                ) as client:
                    self._client = client
                    await client.subscribe(f"{TOPIC_PREFIX}/#", qos=1)
                    logger.info("MQTT connected — subscribed to %s/#", TOPIC_PREFIX)

                    async with client.messages() as messages:
                        async for message in messages:
                            try:
                                raw_payload = message.payload
                                raw = (
                                    raw_payload.decode()
                                    if isinstance(raw_payload, bytes)
                                    else str(raw_payload)
                                )
                                try:
                                    payload = json.loads(raw)
                                except json.JSONDecodeError:
                                    payload = raw
                                msg = MqttMessage(topic=str(message.topic), payload=payload)
                                await self._dispatch(msg)
                            except Exception:
                                logger.exception("Error processing MQTT message")

            except aiomqtt.MqttError as exc:
                logger.warning("MQTT disconnected: %s — reconnecting in 5s", exc)
                self._client = None
                await asyncio.sleep(5)

    async def _dispatch(self, msg: MqttMessage) -> None:
        await self._inbound.put(msg)
        for pattern, handlers in self._subscribers.items():
            if _topic_matches(pattern, msg.topic):
                for handler in handlers:
                    try:
                        result = handler(msg)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception:
                        logger.exception("MQTT handler error for topic %s", msg.topic)

    def subscribe(self, topic_pattern: str, handler: Callable[[MqttMessage], Any]) -> None:
        self._subscribers.setdefault(topic_pattern, []).append(handler)

    async def publish(self, topic: str, payload: dict[str, Any] | str, qos: int = 1) -> None:
        if self._client is None:
            logger.warning("MQTT not connected — dropping publish to %s", topic)
            return
        raw = json.dumps(payload) if isinstance(payload, dict) else payload
        await self._client.publish(topic, raw.encode(), qos=qos)

    async def cmd(self, device_id: str, metric: str, value: Any) -> None:
        """Shorthand: publish a command to quark/cmd/{device-id}/{metric}."""
        topic = f"{TOPIC_PREFIX}/cmd/{device_id}/{metric}"
        await self.publish(topic, {"value": value})


def _topic_matches(pattern: str, topic: str) -> bool:
    parts_p = pattern.split("/")
    parts_t = topic.split("/")
    if len(parts_p) != len(parts_t) and "#" not in pattern:
        return False
    for p, t in zip(parts_p, parts_t):
        if p == "#":
            return True
        if p != "+" and p != t:
            return False
    return len(parts_p) == len(parts_t)


# Singleton instance
mqtt_bridge = MqttBridge()
