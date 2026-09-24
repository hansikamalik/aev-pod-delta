
import { describe, expect, it } from "vitest";
import { Connector } from "../src/connector.js";
import { Asset } from "../src/models.js";

class TestConnector extends Connector {
  readonly name = "test";

  private readonly discoveryFails: boolean;
  private readonly ingestionFails: boolean;

  constructor(options?: {
    discoveryFails?: boolean;
    ingestionFails?: boolean;
  }) {
    super();

    this.discoveryFails = options?.discoveryFails ?? false;
    this.ingestionFails = options?.ingestionFails ?? false;
  }

  async discover(): Promise<Asset[]> {
    if (this.discoveryFails) {
      throw new Error("discovery failure");
    }

    return [
      Asset.parse({
        id: "test-1",
        source: "test",
        type: "compute",
        name: "test-vm",
      }),
    ];
  }

  async ingest(assets: Asset[]): Promise<number> {
    if (this.ingestionFails) {
      throw new Error("ingestion failure");
    }

    return assets.length;
  }

  async checkHealth(): Promise<boolean> {
    return true;
  }

  describeConfig() {
    return {};
  }

  describeCredentials() {
    return {};
  }
}

describe("Connector.sync()", () => {
  it("returns SUCCESS when discovery and ingestion succeed", async () => {
    const connector = new TestConnector();

    const result = await connector.sync();

    expect(result.connector).toBe("test");
    expect(result.status).toBe("success");
    expect(result.assets_discovered).toBe(1);
    expect(result.assets_pushed).toBe(1);
    expect(result.errors).toEqual([]);
  });

  it("returns FAILED when discovery fails", async () => {
    const connector = new TestConnector({
      discoveryFails: true,
    });

    const result = await connector.sync();

    expect(result.status).toBe("failed");
    expect(result.assets_discovered).toBe(0);
    expect(result.assets_pushed).toBe(0);
    expect(result.errors).toEqual([
      "discover() failed: discovery failure",
    ]);
  });

  it("returns FAILED when ingestion fails", async () => {
    const connector = new TestConnector({
      ingestionFails: true,
    });

    const result = await connector.sync();

    expect(result.status).toBe("failed");
    expect(result.assets_discovered).toBe(1);
    expect(result.assets_pushed).toBe(0);
    expect(result.errors).toEqual([
      "ingest() failed: ingestion failure",
    ]);
  });
});