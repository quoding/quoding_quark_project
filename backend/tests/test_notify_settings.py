"""Discord/push notification toggles + the unified notify() dispatcher."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx

from app.main import app
from app.services.notify import (
    is_discord_notify_enabled,
    is_push_notify_enabled,
    notify,
    set_discord_notify_enabled,
    set_push_notify_enabled,
)


async def test_toggles_fail_open_when_redis_unreachable() -> None:
    with patch("app.services.notify.aioredis.Redis") as mock_redis_cls:
        mock_redis_cls.return_value.get = AsyncMock(side_effect=ConnectionError("no redis"))
        assert await is_discord_notify_enabled() is True
        assert await is_push_notify_enabled() is True


async def test_toggle_get_set_roundtrip() -> None:
    store: dict[str, str] = {}

    class _FakeRedis:
        async def get(self, key: str) -> str | None:
            return store.get(key)

        async def set(self, key: str, value: str) -> None:
            store[key] = value

        async def aclose(self) -> None:
            pass

    with patch("app.services.notify.aioredis.Redis", return_value=_FakeRedis()):
        await set_discord_notify_enabled(False)
        assert await is_discord_notify_enabled() is False
        await set_push_notify_enabled(False)
        assert await is_push_notify_enabled() is False


async def test_notify_sends_discord_only_when_push_disabled() -> None:
    with (
        patch("app.services.notify.is_discord_notify_enabled", AsyncMock(return_value=True)),
        patch("app.services.notify.is_push_notify_enabled", AsyncMock(return_value=False)),
        patch("app.services.notify.send_discord_message", new_callable=AsyncMock) as discord_mock,
    ):
        await notify("안녕")
    discord_mock.assert_awaited_once_with("안녕")


async def test_notify_sends_push_only_when_discord_disabled() -> None:
    class _FakeSessionCtx:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *_: object) -> bool:
            return False

    with (
        patch("app.services.notify.is_discord_notify_enabled", AsyncMock(return_value=False)),
        patch("app.services.notify.is_push_notify_enabled", AsyncMock(return_value=True)),
        patch("app.services.notify.send_discord_message", new_callable=AsyncMock) as discord_mock,
        patch("app.core.database.AsyncSessionLocal", return_value=_FakeSessionCtx()),
        patch("app.services.push.send_to_all", new_callable=AsyncMock) as push_mock,
    ):
        await notify("안녕", title="테스트")
    discord_mock.assert_not_called()
    push_mock.assert_awaited_once()
    assert push_mock.await_args.args[1:] == ("테스트", "안녕")


async def test_notify_sends_nothing_when_both_disabled() -> None:
    with (
        patch("app.services.notify.is_discord_notify_enabled", AsyncMock(return_value=False)),
        patch("app.services.notify.is_push_notify_enabled", AsyncMock(return_value=False)),
        patch("app.services.notify.send_discord_message", new_callable=AsyncMock) as discord_mock,
    ):
        await notify("안녕")
    discord_mock.assert_not_called()


# ── /api/system/notify-settings ──────────────────────────────────────────────


async def test_notify_settings_get_and_patch() -> None:
    store: dict[str, str] = {}

    class _FakeRedis:
        async def get(self, key: str) -> str | None:
            return store.get(key)

        async def set(self, key: str, value: str) -> None:
            store[key] = value

        async def aclose(self) -> None:
            pass

    with patch("app.services.notify.aioredis.Redis", return_value=_FakeRedis()):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/system/notify-settings")
            assert resp.json() == {"discord_enabled": True, "push_enabled": True}

            resp = await c.patch("/api/system/notify-settings", json={"discord_enabled": False})
            assert resp.json() == {"discord_enabled": False, "push_enabled": True}
