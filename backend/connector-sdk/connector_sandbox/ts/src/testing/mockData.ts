/**
 * Shared mock data every TS connector's tests reuse. Shape matches
 * the Asset/config/credentials contract in models.ts. Mirrors
 * Python's testing/mock_data.py 1:1.
 */

export const MOCK_ASSETS = [
  {
    id: "vm-001",
    source: "sample",
    type: "compute",
    name: "web-frontend-1",
    raw: { region: "us-east-1", state: "running" },
    tags: { region: "us-east-1" },
  },
  {
    id: "vm-002",
    source: "sample",
    type: "compute",
    name: "web-frontend-2",
    raw: { region: "us-east-1", state: "running" },
    tags: { region: "us-east-1" },
  },
  {
    id: "bucket-001",
    source: "sample",
    type: "storage",
    name: "backups",
    raw: { region: "us-west-2", state: "active" },
    tags: { region: "us-west-2" },
  },
];

export const MOCK_CREDENTIALS = { apiKey: "test-key-do-not-use-in-prod" };

export const MOCK_CONFIG = { region: "us-east-1" };
