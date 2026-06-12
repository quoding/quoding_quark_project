"""Home-control function tools for the QUARK agent.

Every command tool publishes through ``mqtt_bridge.cmd`` / ``publish`` using the
exact topic contract the frontend expects:

    quark/cmd/{device}/{metric}   payload {"value": <v>}

Device / scene ids mirror ``frontend/src/stores/homeStore.ts`` and
``frontend/src/data/quarkData.ts`` so the agent drives the same devices the UI
does. Keep these in sync if the frontend contract changes.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic_ai import RunContext

from app.agents.deps import QuarkDeps
from app.core.config import get_settings
from app.services.host_helper import reboot_host, wake_on_lan

if TYPE_CHECKING:
    from pydantic_ai import Agent

# ── Contract constants (must match the frontend) ─────────────────────────────
LIGHT_ROOMS = ("living", "bed", "desk", "kitchen")
SCENES = ("focus", "sleep", "film", "home", "relax")

_ROOM_KR = {"living": "거실", "bed": "침실", "desk": "책상", "kitchen": "주방"}
_SCENE_KR = {
    "focus": "집중 모드",
    "sleep": "취침 모드",
    "film": "영상 촬영",
    "home": "귀가 모드",
    "relax": "휴식 모드",
}


async def toggle_light(ctx: RunContext[QuarkDeps], room: str, on: bool) -> str:
    """거실/침실/책상/주방 조명을 켜거나 끈다.

    Args:
        room: 조명 위치 — living | bed | desk | kitchen.
        on: True면 켜기, False면 끄기.
    """
    if room not in LIGHT_ROOMS:
        raise ValueError(f"unknown light room: {room!r} (expected one of {LIGHT_ROOMS})")
    await ctx.deps.mqtt.cmd("light", room, on)
    state = "켰어" if on else "껐어"
    return f"{_ROOM_KR[room]} 불 {state} 💡"


async def set_brightness(ctx: RunContext[QuarkDeps], value: int) -> str:
    """조명 밝기를 0~100%로 설정한다."""
    value = max(0, min(100, value))
    await ctx.deps.mqtt.cmd("light", "bright", value)
    return f"밝기 {value}%로 맞췄어."


async def set_led_color(ctx: RunContext[QuarkDeps], color: str) -> str:
    """LED 무드등 색을 설정한다 (hex 예: #3d8bfd)."""
    await ctx.deps.mqtt.cmd("led", "color", color)
    return f"LED 색을 {color}로 바꿨어 🎨"


async def toggle_led(ctx: RunContext[QuarkDeps], on: bool) -> str:
    """LED 무드등을 켜거나 끈다."""
    await ctx.deps.mqtt.cmd("led", "on", on)
    return "LED 켰어 ✨" if on else "LED 껐어."


async def set_ac(
    ctx: RunContext[QuarkDeps], on: bool | None = None, temp: int | None = None
) -> str:
    """에어컨 전원/온도를 설정한다.

    Args:
        on: 전원 상태(선택).
        temp: 설정 온도 ℃ (선택, 16~30).
    """
    if on is None and temp is None:
        raise ValueError("set_ac requires at least one of: on, temp")
    parts: list[str] = []
    if on is not None:
        await ctx.deps.mqtt.cmd("ac", "on", on)
        parts.append("켰어" if on else "껐어")
    if temp is not None:
        temp = max(16, min(30, temp))
        await ctx.deps.mqtt.cmd("ac", "temp", temp)
        parts.append(f"{temp}도로 맞췄어")
    return "에어컨 " + ", ".join(parts) + " ❄️"


async def apply_scene(ctx: RunContext[QuarkDeps], scene: str) -> str:
    """씬(집중/취침/영상촬영/귀가/휴식)을 적용한다.

    Args:
        scene: focus | sleep | film | home | relax.
    """
    if scene not in SCENES:
        raise ValueError(f"unknown scene: {scene!r} (expected one of {SCENES})")
    await ctx.deps.mqtt.cmd("scene", "apply", scene)
    return f"{_SCENE_KR[scene]} 켰어."


async def water_plant(ctx: RunContext[QuarkDeps]) -> str:
    """식물에 물을 준다 (워터펌프 가동)."""
    await ctx.deps.mqtt.cmd("plant", "water", True)
    return "식물에 물 줬어 🌱"


async def reboot_mini_pc(ctx: RunContext[QuarkDeps]) -> str:
    """미니PC(QUARK 서버 본체)를 재부팅한다."""
    ok = await reboot_host()
    return "미니PC를 재부팅할게 — 1~2분 후에 다시 돌아올 거야 🔄" if ok else "재부팅 요청에 실패했어 — 호스트 헬퍼 상태를 확인해줘."


async def wake_laptop(ctx: RunContext[QuarkDeps]) -> str:
    """집 노트북을 Wake-on-LAN으로 깨운다 (전원을 켠다)."""
    mac = get_settings().laptop_mac
    if not mac:
        raise ValueError("laptop_mac이 설정되어 있지 않음")
    ok = await wake_on_lan(mac)
    return "노트북 깨우는 신호 보냈어 — 잠시 후 켜질 거야 💻" if ok else "WoL 신호 전송에 실패했어 — 호스트 헬퍼 상태를 확인해줘."


async def get_home_state(ctx: RunContext[QuarkDeps]) -> dict[str, Any]:
    """현재 집 상태 스냅샷을 읽는다 (제어 명령은 보내지 않음).

    MQTT로 수신된 토픽별 마지막 값을 반환한다. sensor/* 는 실측값,
    cmd/* 는 마지막으로 보낸 명령(기기가 echo하지 않을 때의 추정값)이다.
    """
    snapshot_fn = getattr(ctx.deps.mqtt, "state_snapshot", None)
    state: dict[str, Any] = snapshot_fn() if callable(snapshot_fn) else {}
    if not state:
        return {
            "lights": list(LIGHT_ROOMS),
            "scenes": list(SCENES),
            "note": "아직 수신된 상태 없음 — 기기가 보고하면 quark/# 토픽별 마지막 값이 채워진다.",
        }
    return {"state": state, "lights": list(LIGHT_ROOMS), "scenes": list(SCENES)}


HOME_TOOLS = (
    toggle_light,
    set_brightness,
    set_led_color,
    toggle_led,
    set_ac,
    apply_scene,
    water_plant,
    reboot_mini_pc,
    wake_laptop,
    get_home_state,
)


def register_home_tools(agent: Agent[QuarkDeps, str]) -> None:
    """Register every home-control tool on the given agent."""
    for tool in HOME_TOOLS:
        agent.tool(tool)
