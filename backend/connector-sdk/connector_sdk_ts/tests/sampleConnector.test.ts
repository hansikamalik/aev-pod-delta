import { describe, it, expect } from "vitest";
import { SampleConnector } from "../src/sampleConnector.js";

describe("SampleConnector", () => {
  it("discovers mock VMs", async () => {
    const connector = new SampleConnector();
    const assets = await connector.discover();
    expect(assets.length).toBe(3);
    expect(assets[0].type).toBe("compute");
  });

  it("ingests discovered assets", async () => {
    const connector = new SampleConnector();
    const assets = await connector.discover();
    const pushed = await connector.ingest(assets);
    expect(pushed).toBe(assets.length);
  });

  it("reports healthy", async () => {
    const connector = new SampleConnector();
    expect(await connector.checkHealth()).toBe(true);
  });

  it("runs a full sync", async () => {
    const connector = new SampleConnector();
    const result = await connector.sync();
    expect(result.status).toBe("success");
    expect(result.assetsDiscovered).toBe(3);
    expect(result.assetsPushed).toBe(3);
    expect(result.errors.length).toBe(0);
  });

  it("describes config and credentials", () => {
    const connector = new SampleConnector();
    expect(connector.describeConfig()).toHaveProperty("region");
    expect(connector.describeCredentials()).toHaveProperty("apiKey");
  });
});
