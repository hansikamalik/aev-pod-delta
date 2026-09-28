# Connector SDK (TS) — Interface Guide

Every connector extends `Connector` and implements 6 methods. Worked
example below uses a fictional `OktaConnector` fetching users from
Okta's API.

## 1. `discover(): Promise<Asset[]>`
Read-only. Finds everything visible to this connector; no writes to
the platform.

```ts
async discover(): Promise<Asset[]> {
  const res = await fetch(`${this.baseUrl}/api/v1/users`, {
    headers: { Authorization: `SSWS ${this.apiKey}` },
  });
  const users = await res.json();
  return users.map((u: any) =>
    Asset.parse({
      id: u.id,
      source: this.name,
      type: "identity",
      name: u.profile.login,
      raw: u,
      tags: { status: u.status },
    })
  );
}
```

## 2. `ingest(assets: Asset[]): Promise<number>`
Pushes discovered assets into the platform's asset service. Returns
how many succeeded.

```ts
async ingest(assets: Asset[]): Promise<number> {
  const res = await fetch(`${this.platformUrl}/assets/bulk`, {
    method: "POST",
    body: JSON.stringify(assets),
  });
  const result = await res.json();
  return result.acceptedCount;
}
```

## 3. `sync(): Promise<SyncResult>`
Has a default implementation (discover → ingest, catches errors from
either step) — override only for custom batching/retries.

```ts
// Default is usually enough. Override example (paginated discover):
async sync(): Promise<SyncResult> {
  const startedAt = new Date();
  let pushed = 0, discovered = 0;
  const errors: string[] = [];
  for await (const page of this.discoverPages()) {
    discovered += page.length;
    try {
      pushed += await this.ingest(page);
    } catch (e) {
      errors.push(String(e));
    }
  }
  return SyncResult.parse({
    connector: this.name,
    status: errors.length ? "partial" : "success",
    assetsDiscovered: discovered,
    assetsPushed: pushed,
    errors,
    startedAt,
  });
}
```

## 4. `checkHealth(): Promise<boolean>`
Confirms credentials + network are good, cheaply — don't do a full
discover here.

```ts
async checkHealth(): Promise<boolean> {
  const res = await fetch(`${this.baseUrl}/api/v1/org`, {
    headers: { Authorization: `SSWS ${this.apiKey}` },
  });
  return res.ok;
}
```

## 5. `describeConfig(): Record<string, unknown>`
Non-secret settings the connector needs (region, org URL, etc.).

```ts
describeConfig(): Record<string, unknown> {
  return {
    orgUrl: { type: "string", required: true, description: "e.g. https://your-org.okta.com" },
  };
}
```

## 6. `describeCredentials(): Record<string, unknown>`
Secret fields the connector needs. Never return actual values.

```ts
describeCredentials(): Record<string, unknown> {
  return {
    apiKey: { type: "string", required: true, secret: true },
  };
}
```

---

## Testing your connector

Don't hand-roll test setup. Copy
`tests/sandboxTestHarness.template.test.ts`, fill in the 2 TODOs, and
you get all 6 contract checks running against a real mock HTTP server
(no live Okta/AWS/etc. calls needed). See that file + `contractHarness.ts`
for details.
