
/** Sanity tests for MockApiServer itself, run before trusting it in connector tests. */
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { MOCK_ASSETS } from "../src/testing/mockData.js";
import { MockApiServer } from "../src/testing/mockServer.js";

let server: MockApiServer;

beforeAll(async () => {
  server = await new MockApiServer({ "/assets": MOCK_ASSETS }).start();
});

afterAll(async () => {
  await server.stop();
});

describe("MockApiServer", () => {
  it("starts on a real port and serves a configured route", async () => {
    const res = await fetch(`${server.baseUrl}/assets`);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual(MOCK_ASSETS);
  });

  it("returns 404 for unknown routes", async () => {
    expect((await fetch(`${server.baseUrl}/nope`)).status).toBe(404);
  });

  it("ignores query strings when matching routes", async () => {
    const res = await fetch(`${server.baseUrl}/assets?limit=10`);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual(MOCK_ASSETS);
  });

  it("rejects missing credentials when an API key is configured", async () => {
    const authServer = await new MockApiServer(
      { "/assets": MOCK_ASSETS },
      "expected-test-key",
    ).start();

    try {
      const res = await fetch(`${authServer.baseUrl}/assets`);
      expect(res.status).toBe(401);
    } finally {
      await authServer.stop();
    }
  });

  it("rejects invalid credentials when an API key is configured", async () => {
    const authServer = await new MockApiServer(
      { "/assets": MOCK_ASSETS },
      "expected-test-key",
    ).start();

    try {
      const res = await fetch(`${authServer.baseUrl}/assets`, {
        headers: { Authorization: "Bearer wrong-key" },
      });
      expect(res.status).toBe(401);
    } finally {
      await authServer.stop();
    }
  });

  it("accepts valid credentials when an API key is configured", async () => {
    const authServer = await new MockApiServer(
      { "/assets": MOCK_ASSETS },
      "expected-test-key",
    ).start();

    try {
      const res = await fetch(`${authServer.baseUrl}/assets`, {
        headers: { Authorization: "Bearer expected-test-key" },
      });
      expect(res.status).toBe(200);
      expect(await res.json()).toEqual(MOCK_ASSETS);
    } finally {
      await authServer.stop();
    }
  });
});
