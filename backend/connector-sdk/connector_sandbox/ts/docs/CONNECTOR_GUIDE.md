# Connector SDK (TypeScript): Interface Guide

Every connector extends `Connector` (`src/connector.ts`) and implements six methods. The worked
example is a fictional `OktaConnector` that fetches users from Okta's API. Python equivalent:
[../../docs/DEVELOPER_GUIDE.md](../../docs/DEVELOPER_GUIDE.md).

**Naming.** Model fields are **snake_case** on the wire, matching the Python SDK (`assets_discovered`,
`started_at`, `discovered_at`). Method names are camelCase (`checkHealth`, `describeConfig`). Config
and credential keys are snake_case (`api_key`). See [KNOWN_GAPS](../../docs/KNOWN_GAPS.md) for the open
naming decision.

Set `readonly name = "my_source"` (lowercase letters, digits, underscores). The default is `"unnamed"`,
which the contract suite rejects.

## 1. `discover(): Promise<Asset[]>`

Read-only. Finds everything visible to this connector; never writes to the platform.

```ts
import { Asset, AssetType } from "./models.js";

async discover(): Promise<Asset[]> {
  const res = await fetch(`${this.baseUrl}/api/v1/users`, {
    headers: { Authorization: `SSWS ${this.apiKey}` },
  });
  if (!res.ok) throw new Error(`Okta returned HTTP ${res.status}`);   // don't parse an error body
  const users = await res.json();
  return users.map((u: any) =>
    Asset.parse({
      id: u.id,
      source: this.name,
      type: AssetType.IDENTITY,
      name: u.profile.login,
      raw: u,
      tags: { status: u.status },
    })
  );
}
```

`Asset.parse` validates the shape, so a bad vendor item throws a zod error instead of leaking through.

## 2. `ingest(assets: Asset[]): Promise<number>`

Pushes assets into the platform's asset service. Returns how many succeeded.

```ts
async ingest(assets: Asset[]): Promise<number> {
  const res = await fetch(`${this.platformUrl}/assets/bulk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(assets),
  });
  if (!res.ok) throw new Error(`Platform returned HTTP ${res.status}`);
  const result = await res.json();
  return result.acceptedCount;
}
```

## 3. `sync(): Promise<SyncResult>`

The default runs discover, then ingest, catches errors from either step, and reports `success` or
`failed`. **It never produces `partial`** (an error always means nothing was pushed). Override it when
you need page-by-page ingestion, retries, or partial results:

```ts
import { SyncResult, SyncStatus } from "./models.js";

async sync(): Promise<SyncResult> {
  const startedAt = new Date();
  let discovered = 0, pushed = 0;
  const errors: string[] = [];

  for await (const page of this.discoverPages()) {
    discovered += page.length;
    try {
      pushed += await this.ingest(page);
    } catch (e) {
      errors.push(`ingest() failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  const status =
    errors.length === 0 ? SyncStatus.SUCCESS
    : pushed > 0        ? SyncStatus.PARTIAL
    :                     SyncStatus.FAILED;

  return SyncResult.parse({
    connector: this.name,
    status,
    assets_discovered: discovered,
    assets_pushed: pushed,
    errors,
    started_at: startedAt,          // finished_at defaults to now
  });
}
```

Error strings use the message only (`ingest() failed: ...`), matching Python's output.

## 4. `checkHealth(): Promise<boolean>`

Confirms credentials and network are good, cheaply. Do not run a full discover here.

```ts
async checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${this.baseUrl}/api/v1/org`, {
      headers: { Authorization: `SSWS ${this.apiKey}` },
    });
    return res.ok;
  } catch {
    return false;          // network errors mean "not healthy", not an exception
  }
}
```

## 5. `describeConfig(): JsonSchemaLike`

Non-secret settings, as a JSON-Schema-like object with the full envelope (`type`, `properties`,
`required`). Do not return a flat map of fields.

```ts
describeConfig(): JsonSchemaLike {
  return {
    type: "object",
    properties: {
      org_url: { type: "string", description: "e.g. https://your-org.okta.com" },
    },
    required: ["org_url"],
  };
}
```

## 6. `describeCredentials(): JsonSchemaLike`

Same envelope. Mark secrets with `secret: true`. Never return actual values.

```ts
describeCredentials(): JsonSchemaLike {
  return {
    type: "object",
    properties: {
      api_key: { type: "string", secret: true },
    },
    required: ["api_key"],
  };
}
```

---

## Testing your connector

Copy `tests/sandboxTestHarness.template.test.ts` to `tests/<yourConnector>.contract.test.ts` and fill
in the two TODOs. `runContractSuite(factory)` then runs 7 generic checks (name set; `discover()` returns
an array; `ingest()` returns a count; `sync()` returns a result; `checkHealth()` returns a boolean;
both `describe*` methods return objects) against your connector, using a real local HTTP server
(`MockApiServer`). No live vendor calls are needed.

Run with `npm test` (and `npm run typecheck`) from `ts/`.

**Limits to know about** (details in [KNOWN_GAPS](../../docs/KNOWN_GAPS.md)):

- `MockApiServer` serves fixed JSON per route. It cannot return errors or delays, ignores the HTTP
  method and headers, and returns 404 for any URL with a query string. Keep connector tests to
  query-free `GET` routes for now.
- `MOCK_CREDENTIALS` currently uses `apiKey`; your connector's credential key should be `api_key`.
  Map it in your test factory until the mock data is updated.
- The contract checks are shallow (types only). They will not catch a wrong `describeConfig()` shape,
  so assert that yourself.
- Failure scenarios (401, 500, timeout) are only available in the Python sandbox today.
