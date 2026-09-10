/**
 * Reference implementation of Connector, backed by fake in-memory data.
 * Mirrors Python's sample_connector.py -- pretends to be a cloud provider
 * that exposes a handful of VMs, to prove the TS scaffold end-to-end.
 */
import { Connector } from "./connector.js";
import { Asset } from "./models.js";

interface MockVm {
  id: string;
  name: string;
  region: string;
  state: string;
}

const MOCK_VMS: MockVm[] = [
  { id: "vm-001", name: "web-frontend-1", region: "us-east-1", state: "running" },
  { id: "vm-002", name: "web-frontend-2", region: "us-east-1", state: "running" },
  { id: "vm-003", name: "batch-worker-1", region: "us-west-2", state: "stopped" },
];

export class SampleConnector extends Connector {
  readonly name = "sample";
  private ingested: Asset[] = [];

  async discover(): Promise<Asset[]> {
    return MOCK_VMS.map((vm) =>
      Asset.parse({
        id: vm.id,
        source: this.name,
        type: "compute",
        name: vm.name,
        raw: { ...vm },
        tags: { region: vm.region, state: vm.state },
      })
    );
  }

  async ingest(assets: Asset[]): Promise<number> {
    this.ingested.push(...assets);
    return assets.length;
  }

  async checkHealth(): Promise<boolean> {
    return true;
  }

  describeConfig(): Record<string, unknown> {
    return {
      region: { type: "string", required: true, description: "Region to scan for VMs" },
    };
  }

  describeCredentials(): Record<string, unknown> {
    return {
      apiKey: { type: "string", required: true, secret: true },
    };
  }
}
