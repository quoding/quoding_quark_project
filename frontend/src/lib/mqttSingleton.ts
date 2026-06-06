import mqtt, { type MqttClient } from "mqtt";
import { create } from "zustand";

const MQTT_URL = import.meta.env.VITE_MQTT_URL ?? "ws://localhost:9001";
const MQTT_USER = import.meta.env.VITE_MQTT_USER ?? "quark";
const MQTT_PASS = import.meta.env.VITE_MQTT_PASS ?? "";

interface ConnState {
  connected: boolean;
}

const _connStore = create<ConnState>(() => ({ connected: false }));

export const useMqttConnected = () => _connStore((s) => s.connected);

let _client: MqttClient | null = null;

export function getClient(): MqttClient | null {
  return _client;
}

export function connect(onMessage: (topic: string, payload: Buffer) => void): void {
  if (_client) return;

  const client = mqtt.connect(MQTT_URL, {
    username: MQTT_USER,
    password: MQTT_PASS,
    clientId: `quark-ui-${Math.random().toString(36).slice(2, 10)}`,
    clean: true,
    reconnectPeriod: 5000,
  });

  _client = client;

  client.on("connect", () => {
    _connStore.setState({ connected: true });
    client.subscribe("quark/#", { qos: 1 });
  });
  client.on("disconnect", () => _connStore.setState({ connected: false }));
  client.on("error", () => _connStore.setState({ connected: false }));
  client.on("offline", () => _connStore.setState({ connected: false }));
  client.on("message", onMessage);
}

export function publish(topic: string, value: unknown): void {
  _client?.publish(topic, JSON.stringify({ value }), { qos: 1 });
}

export function cmd(deviceId: string, metric: string, value: unknown): void {
  publish(`quark/cmd/${deviceId}/${metric}`, value);
}
