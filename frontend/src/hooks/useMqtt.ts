import mqtt, { type MqttClient } from "mqtt";
import { useEffect, useRef, useState } from "react";
import { useDeviceStore } from "@/stores/deviceStore";

const MQTT_URL = import.meta.env.VITE_MQTT_URL ?? "ws://localhost:9001";
const MQTT_USER = import.meta.env.VITE_MQTT_USER ?? "quark";
const MQTT_PASS = import.meta.env.VITE_MQTT_PASS ?? "";

// Topic: quark/{type}/{device-id}/{metric}
function parseTopic(topic: string) {
  const [, type, deviceId, metric] = topic.split("/");
  return { type, deviceId, metric };
}

export function useMqtt() {
  const [connected, setConnected] = useState(false);
  const clientRef = useRef<MqttClient | null>(null);
  const { updateMetric, setDevice } = useDeviceStore();

  useEffect(() => {
    const client = mqtt.connect(MQTT_URL, {
      username: MQTT_USER,
      password: MQTT_PASS,
      clientId: `quark-ui-${crypto.randomUUID().slice(0, 8)}`,
      clean: true,
      reconnectPeriod: 5000,
    });

    clientRef.current = client;

    client.on("connect", () => {
      setConnected(true);
      client.subscribe("quark/#", { qos: 1 });
    });

    client.on("disconnect", () => setConnected(false));
    client.on("error", () => setConnected(false));

    client.on("message", (topic, payload) => {
      try {
        const { type, deviceId, metric } = parseTopic(topic);
        if (!deviceId || !metric) return;

        const data = JSON.parse(payload.toString());
        const value = data?.value ?? data;

        if (type === "sensor" || type === "status") {
          // Ensure device exists
          setDevice(deviceId, { id: deviceId, type, name: deviceId });
          updateMetric(deviceId, metric, value);
        }
      } catch {
        // non-JSON payloads — ignore
      }
    });

    return () => {
      client.end(true);
    };
  }, []);

  const publish = (topic: string, value: unknown) => {
    clientRef.current?.publish(topic, JSON.stringify({ value }), { qos: 1 });
  };

  const cmd = (deviceId: string, metric: string, value: unknown) => {
    publish(`quark/cmd/${deviceId}/${metric}`, value);
  };

  return { connected, publish, cmd };
}
