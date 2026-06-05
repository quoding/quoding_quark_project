from __future__ import annotations

from dataclasses import dataclass

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.mqtt_bridge import MqttBridge


@dataclass
class QuarkDeps:
    """Runtime dependencies injected into the QUARK agent via ``RunContext``.

    ``redis`` / ``db`` are optional so the agent can run in contexts (e.g. a
    quick home-control turn or a unit test) where no DB/cache is wired up.
    """

    mqtt: MqttBridge
    redis: aioredis.Redis | None = None
    db: AsyncSession | None = None
