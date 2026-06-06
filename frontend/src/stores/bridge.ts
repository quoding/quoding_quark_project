import { cmd as mqttCmd } from "@/lib/mqttSingleton";

export function cmd(deviceId: string, metric: string, value: unknown): void {
  mqttCmd(deviceId, metric, value);
}
