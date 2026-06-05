/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_MQTT_URL: string;
  readonly VITE_MQTT_USER: string;
  readonly VITE_MQTT_PASS: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
