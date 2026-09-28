/**
 * STARTER TEMPLATE -- copy into your connector's own test file as
 * tests/<yourConnector>.contract.test.ts. Fill in the 2 TODOs.
 *
 * Free with this: a real mock HTTP server (MockApiServer) serving
 * MOCK_ASSETS at GET /assets, plus all 6 contract-compliance checks
 * (see contractHarness.ts) run automatically against whatever
 * connector your factory below builds.
 */
import { afterAll, beforeAll } from "vitest";
import { MOCK_ASSETS, MOCK_CREDENTIALS } from "../src/testing/mockData.js";
import { MockApiServer } from "../src/testing/mockServer.js";
import { runContractSuite } from "../src/testing/contractHarness.js";

// TODO 1: import your real connector
// import { MyNewConnector } from "../src/myNewConnector.js";

let server: MockApiServer;

beforeAll(async () => {
  server = await new MockApiServer({ "/assets": MOCK_ASSETS }).start();
});

afterAll(async () => {
  await server.stop();
});

runContractSuite(() => {
  // TODO 2: instantiate your connector against the mock server
  // return new MyNewConnector({
  //   baseUrl: server.baseUrl,
  //   apiKey: MOCK_CREDENTIALS.apiKey,
  // });
  throw new Error("Wire up your connector in the factory passed to runContractSuite()");
});
