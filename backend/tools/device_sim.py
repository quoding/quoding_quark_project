#!/usr/bin/env python3
"""QUARK device simulator.

Subscribes to quark/cmd/# and echoes each command back as a status update
(quark/cmd/{device}/{metric} → quark/status/{device}/{metric}).
Also publishes periodic sensor data every 10 seconds.

Usage:
    python backend/tools/device_sim.py
    # or via docker-compose quark-device-sim service
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time

import asyncio_mqtt as aiomqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [sim] %(message)s")
log = logging.getLogger(__name__)

BROKER = os.getenv("MQTT_HOST", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))
USER = os.getenv("MQTT_USER", "quark")
PASS = os.getenv("MQTT_PASS", "")


async def _sensor_loop(client: aiomqtt.Client) -> None:
    """Publish synthetic sensor readings every 10 s."""
    while True:
        await asyncio.sleep(10)
        sensors: dict[str, float] = {
            "quark/sensor/temp/value": round(random.uniform(20.0, 26.0), 1),
            "quark/sensor/humidity/value": round(random.uniform(38.0, 62.0), 1),
            "quark/sensor/light/lux": float(random.randint(80, 1200)),
            "quark/sensor/plant/moisture": round(random.uniform(25.0, 70.0), 1),
        }
        for topic, value in sensors.items():
            payload = json.dumps({"value": value, "ts": time.time()})
            await client.publish(topic, payload, qos=0)
        log.info("sensor data published at %s", time.strftime("%H:%M:%S"))


async def main() -> None:
    log.info("connecting to %s:%d …", BROKER, PORT)
    reconnect_delay = 5

    while True:
        try:
            async with aiomqtt.Client(
                hostname=BROKER,
                port=PORT,
                username=USER or None,
                password=PASS or None,
                client_id="quark-device-sim",
                keepalive=60,
            ) as client:
                await client.subscribe("quark/cmd/#", qos=1)
                log.info("subscribed to quark/cmd/#")
                reconnect_delay = 5

                sensor_task = asyncio.create_task(_sensor_loop(client))
                try:
                    async with client.messages() as messages:
                        async for message in messages:
                            topic = str(message.topic)
                            parts = topic.split("/")
                            # quark/cmd/{device}/{metric} → quark/status/{device}/{metric}
                            if len(parts) == 4 and parts[1] == "cmd":
                                status_topic = f"quark/status/{parts[2]}/{parts[3]}"
                                await client.publish(status_topic, message.payload, qos=1)
                                raw = (
                                    message.payload.decode()
                                    if isinstance(message.payload, bytes)
                                    else str(message.payload)
                                )
                                log.info("%s → %s : %s", topic, status_topic, raw)
                finally:
                    sensor_task.cancel()
                    try:
                        await sensor_task
                    except asyncio.CancelledError:
                        pass

        except aiomqtt.MqttError as exc:
            log.warning("MQTT error: %s — reconnecting in %ds", exc, reconnect_delay)
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)


if __name__ == "__main__":
    asyncio.run(main())
