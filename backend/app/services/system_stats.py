from __future__ import annotations

import time
from typing import Any

import psutil


def get_system_stats() -> dict[str, Any]:
    """Return current system stats via psutil.

    Returns: cpu, ram, disk (all int %), temp (float | None), uptime_days (int).
    """
    cpu = int(psutil.cpu_percent(interval=None))
    ram = int(psutil.virtual_memory().percent)
    disk = int(psutil.disk_usage("/").percent)
    uptime_days = int((time.time() - psutil.boot_time()) / 86400)

    temp: float | None = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            # Prefer coretemp or k10temp; fall back to first available sensor
            for key in ("coretemp", "k10temp", "cpu_thermal"):
                if key in temps and temps[key]:
                    temp = round(temps[key][0].current, 1)
                    break
            if temp is None:
                first_group = next(iter(temps.values()))
                if first_group:
                    temp = round(first_group[0].current, 1)
    except (AttributeError, NotImplementedError):
        pass

    return {
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "temp": temp,
        "uptime_days": uptime_days,
    }
