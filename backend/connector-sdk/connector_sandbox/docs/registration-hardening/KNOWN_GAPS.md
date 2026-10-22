# Known Gaps and Open Decisions

A living list. Update it when something is fixed or found. Last reviewed: 28 Sep 2026 (sandbox v0.3.0).

## Resolved since the v3 review

| Item | Resolution |
|---|---|
| `runner.py` crashed (`scenario=` passed to `ReferenceConnector`) | CLI rewritten with `main()`; passes `extra_params`; tested |
| `pyproject.toml` named the project `python-sandbox-v2` | Renamed `python-sandbox` 0.3.0 |
| Console script pointed at a missing `sandbox.cli:app` | Now `sandbox.runner:main` |
| `scenarios` and `connector_sdk` missing from the package list | Added |
| `pydantic` used by the SDK but not declared | Declared |
| Empty `README.md`, stray `Get-ChildItem` file, CRLF line endings, stale `egg-info` | Fixed or removed |
| No package files for the TypeScript half | `package.json` and `tsconfig.json` added |

## Open: contract correctness (highest risk)

| # | Gap | Effect | Suggested fix |
|---|---|---|---|
| 1 | **Two SDK versions.** The sandbox vendors the Week-1 SDK. The repo's `connector-sdk-v0.1.0` has an async `sync()`, `completed_at`, `discoveredAt`, a `(config, credentials)` constructor, name validation (`^[a-z][a-z0-9_]*$`) and `ContractViolation`. Splunk embeds a third, older copy | Connectors written for v0.1.0 (for example `elastic_connector`) cannot run here unchanged | Decide the canonical SDK (decision 1), then port both halves |
| 2 | **Field-name style differs across SDKs** (`discovered_at` vs `discoveredAt`, `finished_at` vs `completed_at`) | Cross-language data can parse with silently wrong defaults | Decide the wire format (decision 2); accept aliases on input, emit one style; add a golden-JSON test |
| 3 | **TS `MOCK_CREDENTIALS` uses `apiKey`**; Python uses `api_key`. The template test comment repeats it | Credential keys are lookup keys, so a mismatch is a runtime "not found" | Rename to `api_key` in `mockData.ts` and the template |
| 4 | **`describe_config()` / `describeConfig()` shape is not asserted** in either language | The flat-map versus schema-envelope drift already happened once | Assert `type`, `properties`, `required` in both contract suites |

## Open: test coverage

| # | Gap | Suggested fix |
|---|---|---|
| 5 | **Mock server does not validate credentials** (Python and TS) | Return 401 for a missing or wrong `Authorization` header; keep `?scenario=unauthorized` as an override |
| 6 | **TS `MockApiServer` is too thin.** It 404s on query strings (`/assets?limit=10`), ignores method and headers, records nothing, and cannot return errors or delays | Match on the path only, check method, record requests, allow per-route status, delay and body; then convert the `it.fails` test |
| 7 | **No reusable Python contract suite** | Provide `contract_suite(make_connector)` as a fixture |
| 8 | **Contract suites are shallow** (types only). TS `ingest()` would accept `NaN` | Validate each asset, `source == name`, unique ids, integer non-negative counts |
| 9 | **No test that an invalid connector is rejected** | Add a subclass missing an abstract method and assert it fails to instantiate |
| 10 | **No Python test for `ingest()` failing** through `sync()` | Add the `SampleConnector(simulate_failure=True)` test in [TESTING.md](TESTING.md) |
| 11 | **`malformed` scenario never reaches its second item**, so the unsupported-type path is untested | Add an `unknown_type` scenario |
| 12 | **`PARTIAL` is unreachable in the default `sync()`** and untested anywhere | Decide whether the default should support partial results, or document that overrides are required |

## Open: behaviour worth deciding

- `ReferenceConnector.discover()` does no payload validation; missing fields become `KeyError`.
- There is no retry, backoff or `Retry-After` handling for 429.
- `check_health()` is the only method that catches HTTP errors itself.
- Only the reference connector exists on the Python side; adding a vendor means editing `server.py` by hand.

## Open: packaging

| # | Gap | Effect | Suggested fix |
|---|---|---|---|
| 13 | **`connector_sdk` is not its own installable package.** The Python Docker image installs from the sandbox's root `pyproject.toml`, which also declares `fastapi`/`uvicorn`/`httpx` — dependencies of the mock server and reference connector, not of the SDK itself | The SDK-only Docker image is heavier than it needs to be | Give `connector_sdk` its own `pyproject.toml` with only `pydantic` as a dependency; point the Dockerfile at that instead |
| 14 | **`POST /connectors/custom` persists nothing and cannot scan or sandbox images.** `InMemoryConnectorRegistry` loses everything on restart, `NotConfiguredScanner` reports `not_scanned`, and nothing pulls or runs the image | Fine for a demo. Registered connectors must not be treated as runnable unless `scan_status` is `passed` | Needs an owner for the scanner and sandbox runtime. See [REGISTRATION_SECURITY.md](REGISTRATION_SECURITY.md) |
| 15 | **No authentication, rate limiting or request-size limit on the registration endpoint** | Anyone who can reach it can register connectors or fill the in-memory store | Decide who may register (see the open questions in [REGISTRATION_READINESS.md](REGISTRATION_READINESS.md)); add auth and limits at the gateway or route |
| 16 | **The registry allowlist is an environment variable** (`ALLOWED_REGISTRIES`) and defaults to deny-all | An unset variable rejects every registration, which is safe but easy to mistake for a bug | Document it in the deployment config; decide who owns the list |

## Open: hygiene

- `live_server` starts a server per test (suite takes about 20 s); a session-scoped fixture would be faster.
- `python/fixtures/reference/success/assets.json` is unused and duplicates data inlined in `server.py`.
- Only Windows has been verified. Run once on Linux and macOS, ideally in CI.
- `vitest.config.ts` replaces vitest's default excludes; extend `configDefaults.exclude` instead.
- Deprecation warning: `starlette.testclient` with `httpx`.
- Three unrelated fixture sets exist (`asset-001...`, `vm-001...`, `i-0abc123...`).

## Open decisions

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | Canonical SDK | Week-1 pydantic SDK, or repo `connector-sdk-v0.1.0` | v0.1.0 if other squads already build against it (several connectors in the repo import it) |
| 2 | Wire format and field names | snake_case everywhere, or `discoveredAt` on the wire | Follow the written contract; convert at one boundary; do not alias credential/config keys |
| 3 | Should `name != "unnamed"` be required by the contract? | Enforce in the SDK, or drop the check | Enforce in the SDK so both languages agree |
| 4 | Should 429 be retried by the connector or only reported? | Report only, or retry with backoff | Decide per contract; the sandbox can test either |
