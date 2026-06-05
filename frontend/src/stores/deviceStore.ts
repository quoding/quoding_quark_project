import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";

export type DeviceStatus = "online" | "offline" | "unknown";

export interface Device {
  id: string;
  name: string;
  type: "light" | "sensor" | "plant" | "switch" | "camera" | string;
  status: DeviceStatus;
  lastSeen: number;
  metrics: Record<string, number | string | boolean>;
}

interface DeviceStore {
  devices: Record<string, Device>;
  setDevice: (id: string, device: Partial<Device>) => void;
  updateMetric: (deviceId: string, metric: string, value: number | string | boolean) => void;
  setStatus: (deviceId: string, status: DeviceStatus) => void;
  getDevice: (id: string) => Device | undefined;
}

export const useDeviceStore = create<DeviceStore>()(
  subscribeWithSelector((set, get) => ({
    devices: {},

    setDevice: (id, partial) =>
      set((state) => ({
        devices: {
          ...state.devices,
          [id]: { ...state.devices[id], ...partial, id } as Device,
        },
      })),

    updateMetric: (deviceId, metric, value) =>
      set((state) => {
        const device = state.devices[deviceId];
        if (!device) return state;
        return {
          devices: {
            ...state.devices,
            [deviceId]: {
              ...device,
              metrics: { ...device.metrics, [metric]: value },
              lastSeen: Date.now(),
            },
          },
        };
      }),

    setStatus: (deviceId, status) =>
      set((state) => {
        const device = state.devices[deviceId];
        if (!device) return state;
        return {
          devices: {
            ...state.devices,
            [deviceId]: { ...device, status },
          },
        };
      }),

    getDevice: (id) => get().devices[id],
  }))
);
