"""Each home-control tool publishes the frontend-contract MQTT topic/payload."""
from __future__ import annotations

from typing import Any

import pytest

from app.tools.home import (
    apply_scene,
    get_home_state,
    set_ac,
    set_brightness,
    set_led_color,
    toggle_led,
    toggle_light,
    water_plant,
)


async def test_toggle_light_living_off(ctx: Any) -> None:
    await toggle_light(ctx, room="living", on=False)
    ctx.deps.mqtt.publish.assert_awaited_once_with("quark/cmd/light/living", {"value": False})


async def test_toggle_light_rejects_unknown_room(ctx: Any) -> None:
    with pytest.raises(ValueError):
        await toggle_light(ctx, room="garage", on=True)
    ctx.deps.mqtt.publish.assert_not_awaited()


async def test_set_brightness_clamps_and_publishes(ctx: Any) -> None:
    await set_brightness(ctx, 150)
    ctx.deps.mqtt.publish.assert_awaited_once_with("quark/cmd/light/bright", {"value": 100})


async def test_set_led_color(ctx: Any) -> None:
    await set_led_color(ctx, "#ffffff")
    ctx.deps.mqtt.publish.assert_awaited_once_with("quark/cmd/led/color", {"value": "#ffffff"})


async def test_toggle_led(ctx: Any) -> None:
    await toggle_led(ctx, on=False)
    ctx.deps.mqtt.publish.assert_awaited_once_with("quark/cmd/led/on", {"value": False})


async def test_set_ac_both_fields(ctx: Any) -> None:
    await set_ac(ctx, on=True, temp=24)
    ctx.deps.mqtt.publish.assert_any_await("quark/cmd/ac/on", {"value": True})
    ctx.deps.mqtt.publish.assert_any_await("quark/cmd/ac/temp", {"value": 24})


async def test_apply_scene(ctx: Any) -> None:
    await apply_scene(ctx, "sleep")
    ctx.deps.mqtt.publish.assert_awaited_once_with("quark/cmd/scene/apply", {"value": "sleep"})


async def test_apply_scene_rejects_unknown(ctx: Any) -> None:
    with pytest.raises(ValueError):
        await apply_scene(ctx, "party")


async def test_water_plant(ctx: Any) -> None:
    await water_plant(ctx)
    ctx.deps.mqtt.publish.assert_awaited_once_with("quark/cmd/plant/water", {"value": True})


async def test_get_home_state_is_read_only(ctx: Any) -> None:
    state = await get_home_state(ctx)
    assert "lights" in state and "scenes" in state
    ctx.deps.mqtt.publish.assert_not_awaited()
