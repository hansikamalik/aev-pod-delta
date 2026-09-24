/**
 * Reference implementation of Connector, using fake in-memory data.
 *
 * This is the "one working example connector" deliverable for Week 1.
 * New connector authors can copy this file as a starting point.
 *
 * Mirrors Python's sample_connector.py exactly: same fixture rows, same
 * kind->type mapping, same failure-simulation switch, same schema shapes.
 */

import { Connector, JsonSchemaLike } from "./connector.js";
import { Asset, AssetType } from "./models.js";

interface SourceRow {
  id: string;
  name: string;
  kind: string;
}

// Fake data standing in for a real source system (e.g. a cloud API).
const FAKE_SOURCE_DATA: SourceRow[] = [
  { id: "i-0abc123", name: "web-server-1", kind: "vm" },
  { id: "i-0def456", name: "worker-node-2", kind: "vm" },
  { id: "bkt-9f8e7d", name: "app-uploads", kind: "bucket" },
];

const KIND_TO_TYPE: Record<string, AssetType> = {
  vm: AssetType.COMPUTE,
  bucket: AssetType.STORAGE,
};

/**
 * A minimal, fully working connector against fake data.
 *
 * Real connectors (AWS, Okta, Splunk, ...) follow this exact shape --
 * only discover()/ingest()/checkHealth() change to talk to a real API.
 */
export class SampleConnector extends Connector {
  readonly name = "sample";

  private readonly simulateFailure: boolean;

  /** Stand-in for the platform's asset store. */
  private pushedAssets: Asset[] = [];

  constructor(simulateFailure = false) {
    super();
    this.simulateFailure = simulateFailure;
  }

  async discover(): Promise<Asset[]> {
    return FAKE_SOURCE_DATA.map((item) =>
      Asset.parse({
        id: item.id,
        source: this.name,
        type: KIND_TO_TYPE[item.kind] ?? AssetType.OTHER,
        name: item.name,
        raw: { ...item },
      })
    );
  }

  async ingest(assets: Asset[]): Promise<number> {
    if (this.simulateFailure) {
      throw new Error("simulated push failure");
    }
    this.pushedAssets.push(...assets);
    return assets.length;
  }

  async checkHealth(): Promise<boolean> {
    // A real connector would ping its API here.
    return !this.simulateFailure;
  }

  describeConfig(): JsonSchemaLike {
    return {
      type: "object",
      properties: {
        region: { type: "string", description: "Fake region, unused" },
      },
      required: [],
    };
  }

  describeCredentials(): JsonSchemaLike {
    return {
      type: "object",
      properties: {
        api_key: { type: "string", secret: true },
      },
      required: ["api_key"],
    };
  }
}