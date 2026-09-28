/**
 * Runs the shared contract suite against the SDK's own SampleConnector.
 * This is the "does the harness itself work" test -- it needs no mock
 * server because SampleConnector uses in-memory fake data.
 */
import { describe, expect, it } from "vitest";
import { SampleConnector } from "../src/sampleConnector.js";
import { SyncStatus } from "../src/models.js";
import { runContractSuite } from "../src/testing/contractHarness.js";

runContractSuite(() => new SampleConnector());

describe("SampleConnector behaviour beyond the contract suite", () => {
  it("maps kinds to asset types, with vm -> compute and bucket -> storage", async () => {
    const assets = await new SampleConnector().discover();
    expect(assets.map((a) => a.type)).toEqual(["compute", "compute", "storage"]);
  });

  it("reports FAILED when ingest() throws (simulate_failure)", async () => {
    const result = await new SampleConnector(true).sync();
    expect(result.status).toBe(SyncStatus.FAILED);
    expect(result.assets_pushed).toBe(0);
    expect(result.errors[0]).toBe("ingest() failed: simulated push failure");
  });

  it("checkHealth() is false when simulating failure", async () => {
    expect(await new SampleConnector(true).checkHealth()).toBe(false);
  });
});
