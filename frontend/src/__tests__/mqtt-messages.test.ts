import { beforeEach, describe, expect, it, vi } from "vitest";

describe("handleMessage", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("updates deviceStore metric on sensor message", async () => {
    const mockUpdateMetric = vi.fn();
    const mockSetDevice = vi.fn();

    vi.doMock("@/stores/deviceStore", () => ({
      useDeviceStore: {
        getState: () => ({ setDevice: mockSetDevice, updateMetric: mockUpdateMetric }),
      },
    }));
    vi.doMock("@/stores/homeStore", () => ({
      useHomeStore: {
        getState: () => ({ lights: {}, bright: 0 }),
        setState: vi.fn(),
      },
    }));

    const { handleMessage } = await import("@/lib/mqttMessages");
    handleMessage(
      "quark/sensor/temp/value",
      Buffer.from(JSON.stringify({ value: 23.5 })),
    );

    expect(mockSetDevice).toHaveBeenCalled();
    expect(mockUpdateMetric).toHaveBeenCalledWith("temp", "value", 23.5);
  });

  it("mirrors homeStore lights on quark/status/light/{room}", async () => {
    const mockSetState = vi.fn();

    vi.doMock("@/stores/deviceStore", () => ({
      useDeviceStore: {
        getState: () => ({ setDevice: vi.fn(), updateMetric: vi.fn() }),
      },
    }));
    vi.doMock("@/stores/homeStore", () => ({
      useHomeStore: {
        getState: () => ({ lights: { living: false }, bright: 50 }),
        setState: mockSetState,
      },
    }));

    const { handleMessage } = await import("@/lib/mqttMessages");
    handleMessage(
      "quark/status/light/living",
      Buffer.from(JSON.stringify({ value: true })),
    );

    expect(mockSetState).toHaveBeenCalled();
    const arg = mockSetState.mock.calls[0][0] as { lights?: Record<string, boolean> };
    expect(arg.lights?.living).toBe(true);
  });

  it("does not throw on non-JSON payload", async () => {
    vi.doMock("@/stores/deviceStore", () => ({
      useDeviceStore: {
        getState: () => ({ setDevice: vi.fn(), updateMetric: vi.fn() }),
      },
    }));
    vi.doMock("@/stores/homeStore", () => ({
      useHomeStore: {
        getState: () => ({ lights: {} }),
        setState: vi.fn(),
      },
    }));

    const { handleMessage } = await import("@/lib/mqttMessages");
    expect(() => {
      handleMessage("quark/sensor/a/b", Buffer.from("not-json"));
    }).not.toThrow();
  });
});
