"""Web push (VAPID) — send notifications to subscriptions saved via /api/push/subscribe."""
from __future__ import annotations

import json
import logging

from pywebpush import WebPushException, webpush_async
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.push import PushSubscription

logger = logging.getLogger(__name__)


async def send_to_all(db: AsyncSession, title: str, body: str) -> dict[str, int]:
    """Send *title*/*body* to every stored subscription.

    Drops subscriptions the push service reports as gone (404/410 — the user
    uninstalled the PWA or revoked permission) so the table doesn't grow stale.
    """
    settings = get_settings()
    result = await db.execute(select(PushSubscription))
    subs = list(result.scalars().all())

    payload = json.dumps({"title": title, "body": body})
    sent = 0
    removed = 0
    for sub in subs:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
        }
        try:
            await webpush_async(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
            )
            sent += 1
        except WebPushException as exc:
            status = exc.response.status if exc.response is not None else None
            if status in (404, 410):
                await db.execute(delete(PushSubscription).where(PushSubscription.id == sub.id))
                removed += 1
            else:
                logger.warning("Push send failed (status=%s): %s", status, exc, exc_info=True)
        except Exception:
            logger.warning("Push send failed", exc_info=True)

    if removed:
        await db.commit()
    return {"sent": sent, "removed": removed}


async def send_test(db: AsyncSession) -> dict[str, int]:
    return await send_to_all(db, "QUARK", "테스트 알림이야 — 여기까지 오면 웹 푸시 성공!")
