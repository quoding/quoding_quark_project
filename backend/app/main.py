from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.core.redis import close_pool
from app.routers import agenda, automations, chat, devices, habits, health, ideas, memo, push, research, siri, system, todos, tracking, water
from app.services.mqtt_bridge import mqtt_bridge
from app.services.rule_router import rule_router
from app.services.scheduler import start_scheduler, stop_scheduler

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("QUARK API starting — env=%s", settings.environment)

    await init_db()
    await mqtt_bridge.start()
    rule_router.load_defaults()
    start_scheduler()

    yield

    logger.info("QUARK API shutting down")
    stop_scheduler()
    await mqtt_bridge.stop()
    await close_pool()


app = FastAPI(
    title="QUARK API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://quark.quoding.com"] if settings.environment == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router, prefix="/api")
app.include_router(devices.router, prefix="/api")
app.include_router(agenda.router, prefix="/api")
app.include_router(todos.router, prefix="/api")
app.include_router(habits.router, prefix="/api")
app.include_router(ideas.router, prefix="/api")
app.include_router(memo.router, prefix="/api")
app.include_router(automations.router, prefix="/api")
app.include_router(water.router, prefix="/api")
app.include_router(tracking.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(siri.router, prefix="/api")
app.include_router(research.router, prefix="/api")
app.include_router(push.router, prefix="/api")
