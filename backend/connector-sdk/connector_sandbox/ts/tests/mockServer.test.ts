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

  // KNOWN GAP (from the harness review): the server matches on the raw URL,
  // query string included. Flip this to a normal `it` once mockServer.ts is fixed.
  it.fails("ignores the query string when matching routes", async () => {
    expect((await fetch(`${server.baseUrl}/assets?limit=10`)).status).toBe(200);
  });
});
