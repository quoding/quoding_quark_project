import { useDeviceStore } from "@/stores/deviceStore";
import { useHomeStore } from "@/stores/homeStore";
import type { LightKey } from "@/types/quark";

function parseTopic(topic: string) {
  const parts = topic.split("/");
  return { type: parts[1], deviceId: parts[2], metric: parts[3] };
}

export function handleMessage(topic: string, payload: Buffer): void {
  try {
    const { type, deviceId, metric } = parseTopic(topic);
    if (!type || !deviceId || !metric) return;

    const data = JSON.parse(payload.toString()) as Record<string, unknown>;
    const value = data?.value ?? data;

    const { setDevice, updateMetric } = useDeviceStore.getState();

    if (type === "sensor" || type === "status") {
      setDevice(deviceId, { id: deviceId, type, name: deviceId });
      updateMetric(deviceId, metric, value as number | string | boolean);
    }

    // Mirror light status into homeStore without re-publishing a cmd
    if (type === "status" && deviceId === "light") {
      if (metric === "bright") {
        useHomeStore.setState({ bright: Number(value) });
      } else {
        const lights = useHomeStore.getState().lights;
        useHomeStore.setState({ lights: { ...lights, [metric as LightKey]: Boolean(value) } });
      }
    }
  } catch {
    // non-JSON payload — ignore
  }
}
