/**
 * Reusable vitest suite asserting a Connector implementation
 * satisfies the frozen contract (6 methods). Call runContractSuite()
 * with a factory that builds your connector -- get all 6 checks free.
 * Mirrors Python's testing/contract_harness.py.
 */
import { describe, expect, it } from "vitest";
import { Connector } from "../connector.js";

export function runContractSuite(makeConnector: () => Connector | Promise<Connector>) {
  describe("Connector contract", () => {
    it("has a real name set", async () => {
      const connector = await makeConnector();
      expect(connector.name).toBeTruthy();
      expect(connector.name).not.toBe("unnamed");
    });

    it("discover() returns assets", async () => {
      const connector = await makeConnector();
      const assets = await connector.discover();
      expect(Array.isArray(assets)).toBe(true);
    });

    it("ingest() returns a count", async () => {
      const connector = await makeConnector();
      const assets = await connector.discover();
      const pushed = await connector.ingest(assets);
      expect(typeof pushed).toBe("number");
      expect(pushed).toBeLessThanOrEqual(assets.length);
    });

    it("sync() returns a SyncResult", async () => {
      const connector = await makeConnector();
      const result = await connector.sync();
      expect(["success", "partial", "failed"]).toContain(result.status);
      expect(result.connector).toBe(connector.name);
    });

    it("checkHealth() returns a boolean", async () => {
      const connector = await makeConnector();
      expect(typeof (await connector.checkHealth())).toBe("boolean");
    });

    it("describeConfig() returns an object", async () => {
      const connector = await makeConnector();
      expect(typeof connector.describeConfig()).toBe("object");
    });

    it("describeCredentials() returns an object", async () => {
      const connector = await makeConnector();
      expect(typeof connector.describeCredentials()).toBe("object");
    });
  });
}
