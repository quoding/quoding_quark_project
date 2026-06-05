from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


def start_scheduler() -> None:
    scheduler.add_job(
        _morning_brief,
        trigger=CronTrigger(hour=8, minute=0),
        id="morning-brief",
        replace_existing=True,
    )
    scheduler.add_job(
        _sensor_poll,
        trigger=IntervalTrigger(seconds=30),
        id="sensor-poll",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — %d jobs registered", len(scheduler.get_jobs()))


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)


async def _morning_brief() -> None:
    """Daily 08:00 KST — generate and send morning summary via Discord."""
    logger.info("Running morning brief")
    # TODO: wire to brief agent


async def _sensor_poll() -> None:
    """Every 30s — request sensor data from ESP32 devices via MQTT."""
    from app.services.mqtt_bridge import mqtt_bridge

    await mqtt_bridge.publish("quark/cmd/all/poll", {"ts": __import__("time").time()})
