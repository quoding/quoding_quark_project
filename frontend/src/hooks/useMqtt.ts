import { useEffect } from "react";
import { connect } from "@/lib/mqttSingleton";
import { handleMessage } from "@/lib/mqttMessages";

let _initialized = false;

export function useMqtt(): void {
  useEffect(() => {
    if (_initialized) return;
    _initialized = true;
    connect(handleMessage);
  }, []);
}
