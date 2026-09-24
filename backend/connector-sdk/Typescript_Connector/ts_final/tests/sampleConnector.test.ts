
import { describe, expect, it } from "vitest";
import { SampleConnector } from "../src/sampleConnector.js";

describe("SampleConnector", () => {
  it("discovers the same 3 assets as the Python connector", async () => {
    const connector = new SampleConnector();

    const assets = await connector.discover();

    expect(assets).toHaveLength(3);

    expect(assets).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: "i-0abc123",
          source: "sample",
          type: "compute",
          name: "web-server-1",
        }),
        expect.objectContaining({
          id: "i-0def456",
          source: "sample",
          type: "compute",
          name: "worker-node-2",
        }),
        expect.objectContaining({
          id: "bkt-9f8e7d",
          source: "sample",
          type: "storage",
          name: "app-uploads",
        }),
      ]),
    );
  });

  it("preserves the original source row in raw", async () => {
    const connector = new SampleConnector();

    const assets = await connector.discover();

    expect(assets[0].raw).toEqual({
      id: "i-0abc123",
      name: "web-server-1",
      kind: "vm",
    });

    expect(assets[2].raw).toEqual({
      id: "bkt-9f8e7d",
      name: "app-uploads",
      kind: "bucket",
    });
  });

  it("ingests all discovered assets", async () => {
    const connector = new SampleConnector();

    const assets = await connector.discover();
    const pushed = await connector.ingest(assets);

    expect(pushed).toBe(3);
  });

  it("reports healthy when failure simulation is disabled", async () => {
    const connector = new SampleConnector();

    await expect(connector.checkHealth()).resolves.toBe(true);
  });

  it("reports unhealthy when failure simulation is enabled", async () => {
    const connector = new SampleConnector(true);

    await expect(connector.checkHealth()).resolves.toBe(false);
  });

  it("runs a successful sync", async () => {
    const connector = new SampleConnector();

    const result = await connector.sync();

    expect(result.connector).toBe("sample");
    expect(result.status).toBe("success");
    expect(result.assets_discovered).toBe(3);
    expect(result.assets_pushed).toBe(3);
    expect(result.errors).toEqual([]);
    expect(result.started_at).toBeInstanceOf(Date);
    expect(result.finished_at).toBeInstanceOf(Date);
  });

  it("runs the same failure path as Python", async () => {
    const connector = new SampleConnector(true);

    const result = await connector.sync();

    expect(result.connector).toBe("sample");
    expect(result.status).toBe("failed");
    expect(result.assets_discovered).toBe(3);
    expect(result.assets_pushed).toBe(0);
    expect(result.errors).toEqual([
      "ingest() failed: simulated push failure",
    ]);
  });

  it("returns the Python-compatible config schema", () => {
    const connector = new SampleConnector();

    expect(connector.describeConfig()).toEqual({
      type: "object",
      properties: {
        region: {
          type: "string",
          description: "Fake region, unused",
        },
      },
      required: [],
    });
  });

  it("returns the Python-compatible credential schema", () => {
    const connector = new SampleConnector();

    expect(connector.describeCredentials()).toEqual({
      type: "object",
      properties: {
        api_key: {
          type: "string",
          secret: true,
        },
      },
      required: ["api_key"],
    });
  });
});

