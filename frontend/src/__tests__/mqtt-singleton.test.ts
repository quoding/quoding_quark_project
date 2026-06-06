import { beforeEach, describe, expect, it, vi } from "vitest";

describe("mqttSingleton", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("publish serialises value as JSON and forwards to mqtt client", async () => {
    const mockPublish = vi.fn();
    vi.doMock("mqtt", () => ({
      default: {
        connect: vi.fn(() => ({
          on: vi.fn(),
          publish: mockPublish,
          subscribe: vi.fn(),
        })),
      },
    }));

    const mod = await import("@/lib/mqttSingleton");
    mod.connect(vi.fn());
    mod.publish("quark/test/topic", 99);

    expect(mockPublish).toHaveBeenCalledWith(
      "quark/test/topic",
      JSON.stringify({ value: 99 }),
      { qos: 1 },
    );
  });

  it("cmd constructs correct quark/cmd/{device}/{metric} topic", async () => {
    const mockPublish = vi.fn();
    vi.doMock("mqtt", () => ({
      default: {
        connect: vi.fn(() => ({
          on: vi.fn(),
          publish: mockPublish,
          subscribe: vi.fn(),
        })),
      },
    }));

    const mod = await import("@/lib/mqttSingleton");
    mod.connect(vi.fn());
    mod.cmd("led", "color", "#ff0000");

    expect(mockPublish).toHaveBeenCalledWith(
      "quark/cmd/led/color",
      JSON.stringify({ value: "#ff0000" }),
      { qos: 1 },
    );
  });

  it("connect ignores second call — singleton guard", async () => {
    const mockConnect = vi.fn(() => ({
      on: vi.fn(),
      publish: vi.fn(),
      subscribe: vi.fn(),
    }));
    vi.doMock("mqtt", () => ({ default: { connect: mockConnect } }));

    const mod = await import("@/lib/mqttSingleton");
    mod.connect(vi.fn());
    mod.connect(vi.fn());

    expect(mockConnect).toHaveBeenCalledTimes(1);
  });
});
