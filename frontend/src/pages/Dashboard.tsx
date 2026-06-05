import { useMqtt } from "@/hooks/useMqtt";
import { useDeviceStore } from "@/stores/deviceStore";

export default function Dashboard() {
  const { connected } = useMqtt();
  const devices = useDeviceStore((s) => s.devices);

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-semibold">QUARK Dashboard</h1>
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            connected
              ? "bg-green-900 text-green-300"
              : "bg-red-900 text-red-300"
          }`}
        >
          MQTT {connected ? "연결됨" : "끊김"}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {Object.values(devices).length === 0 ? (
          <p className="text-muted-foreground col-span-full text-sm">
            기기를 기다리는 중... (ESP32 연결 후 자동 표시됩니다)
          </p>
        ) : (
          Object.values(devices).map((device) => (
            <div
              key={device.id}
              className="rounded-lg border border-border bg-card p-4"
            >
              <p className="font-medium text-sm">{device.name || device.id}</p>
              <p className="text-xs text-muted-foreground mb-2">{device.type}</p>
              {Object.entries(device.metrics).map(([k, v]) => (
                <div key={k} className="flex justify-between text-xs">
                  <span className="text-muted-foreground">{k}</span>
                  <span>{String(v)}</span>
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
