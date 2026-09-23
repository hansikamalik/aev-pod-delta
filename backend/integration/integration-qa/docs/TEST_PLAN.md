# QA Test Plan — Integration Squad, Week 1

Owner: Bhawook Priyam (QA, Automation & Documentation)
Principle: testing begins Day 1 against mocks and fixtures; it never waits for development.

## Scope per workstream

| Workstream (owner) | Test suite | Status gate |
|---|---|---|
| Connector contract (Harshal) | `tests/contract/` — full §25 matrix + §26 minimum suite: interface, stable identity (§6), source equality (§7), AssetType (§8), ingest counting (§11), idempotency (§12), SyncResult (§14–15), error/secret hygiene (§16, §19), config/credential schemas (§18–19) | P0, blocks every PR |
| Azure auth (Bhavesh K) | `tests/azure/test_azure.py::TestAzureAuth` — valid/expired/incomplete creds, token caching | Day 3 |
| Azure discovery (Subramani) | `TestAzureDiscovery` — all 5 resource types, pagination, error wrapping | Day 3 |
| Azure normalize + push (Ashwin) | `TestAzureNormalization`, `TestAzurePush` — schema validity, id preservation, failure reporting | Day 3 |
| Splunk connector (Ayyappatadi) | `tests/splunk/` — token auth, forwarding, 5xx retries, normalization, health | Day 5 |
| Vault / scheduler / lock (Abhiram) | `tests/infra/` — retrieval, missing-secret errors, trigger/stop, exclusivity, duplicate-run prevention | Day 5 |
| End-to-end (all) | `tests/integration/` — Vault→creds→connector→push; cron→lock→sync | Day 6–7 |
| Regression (Bhawook) | `tests/regression/` — contract baseline, secrets scan, suite speed | Day 7 + every merge |

## Test strategy

1. **Contract tests are the P0 gate.** Every connector (dummy, Azure, Splunk) must
   pass the same suite; new connectors are one line in `all_connectors()`.
2. **Mocks over real APIs.** All module tests run against `qa/mocks/` and
   `qa/fixtures/` — deterministic, fast, no cost, no flake.
3. **Graceful skips.** Tests target modules via `module_or_skip()`; unimplemented
   modules skip with a named reason, keeping CI green during parallel dev.
4. **Schema-first validation.** Every normalized asset is validated against
   `qa/schemas/asset.schema.json` — the QA mirror of contract_v2 §5–§9
   (required: id, source, type, name, raw, discoveredAt; AssetType enum per §8).
5. **Security gates.** Automated scan for hardcoded credentials; vault-derived
   credentials only; no plaintext secrets in logs.

## Entry / exit criteria

- **Entry:** shared contract spec agreed (Harshal), fixtures reviewed.
- **Exit (Day 7):** 0 failures, contract suite green for all connectors,
  integration suite green end-to-end, regression green, coverage reported,
  documentation updated, CI green on main.

## Risks / open items

- [ ] Official connector contract spec from Harshal — QA mirror in `qa/contracts.py` must be reconciled
- [ ] Real module import paths — update `TARGET_MODULES` in `tests/conftest.py`
- [ ] Platform asset-push API shape — confirm with Ashwin when push module lands
- [ ] CI repo layout (monorepo vs per-module) — confirm with Harshal Day 1
