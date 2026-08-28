"""Run-time gate for fixed automations (APScheduler cron jobs, rule_router rules).

User macros (kind="macro") already check ``Automation.enabled`` themselves in
``app/tools/assistant.py::run_automation``. Fixed automations (kind="cron" /
"mqtt_rule") are registered unconditionally at startup, so their execution
functions call ``is_enabled(db, slug)`` at the top and bail out if the user
turned them off — see app/services/scheduler.py and app/services/rule_router.py.
"""
from __future__ import annotations

import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agenda import Automation

logger = logging.getLogger(__name__)


async def is_enabled(db: AsyncSession, slug: str) -> bool:
    """True if the automation is on — also true (fail-open) if its row doesn't exist yet."""
    result = await db.execute(select(Automation.enabled).where(Automation.slug == slug))
    row = result.scalar_one_or_none()
    return True if row is None else bool(row)


async def mark_run(db: AsyncSession, slug: str) -> None:
    """Best-effort run_count bump — never let a stats update block the real work."""
    try:
        await db.execute(
            update(Automation).where(Automation.slug == slug).values(run_count=Automation.run_count + 1)
        )
        await db.commit()
    except Exception:
        logger.warning("Failed to bump run_count for automation %s", slug, exc_info=True)
