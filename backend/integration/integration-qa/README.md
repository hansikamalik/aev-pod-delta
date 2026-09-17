# Integration Squad — QA, Automation & Documentation (Bhawook Priyam)

pytest-based test framework covering the whole Week-1 Integration workload:
connector contract tests, Azure / Splunk / Vault / scheduler / lock module
tests, an end-to-end integration suite, and a regression suite.

**Design rule (from the week plan):** nothing waits for anyone. Tests that
target teammates' modules auto-**skip** with a clear reason until the module
lands — the suite is green on Day 1 and lights up area by area.

## Layout

```
integration-qa/
├── pytest.ini                  # markers, strict mode, coverage config
├── requirements-dev.txt
├── Makefile                    # make test | contract | coverage | report | ci
├── ci/github-actions.yml       # CI pipeline (copy to .github/workflows/)
├── qa/                         # QA toolkit (not tests — support code)
│   ├── contracts.py            # QA mirror of the shared Connector contract
│   ├── validators.py           # common-asset schema validation
│   ├── schemas/asset.schema.json
│   ├── mocks/                  # dummy connector, mock Azure/Splunk/Vault
│   └── fixtures/               # Azure resource JSON, Splunk events
├── tests/
│   ├── conftest.py             # fixtures + module_or_skip() resolver
│   ├── contract/               # P0 gate — runs against EVERY connector
│   ├── azure/                  # auth, discovery, normalization, push
│   ├── splunk/                 # token auth, forwarding, retries, health
│   ├── infra/                  # vault, cron scheduler, distributed lock
│   ├── integration/            # end-to-end (Day 6–7)
│   └── regression/             # post-merge + Day 7 gate
└── docs/
    ├── TEST_PLAN.md            # what's tested, mapped to the week schedule
    └── TEST_REPORT_TEMPLATE.md # final deliverable template
```

## Daily usage

```bash
pip install -r requirements-dev.txt
make contract      # P0 contract gate
make test          # fast inner loop
make coverage      # coverage for the weekly report
make report        # HTML report for the final deliverable
make ci            # what CI runs
```

## Current status

```
32 passed, 37 skipped   # skipped = waiting on teammates' modules (by design)
```

## Contract alignment

Aligned to **contract_v2** (Connector SDK — Integration Connector Contract):
`Asset(id, source, type, name, raw, discoveredAt, tags)`, `AssetType` =
compute/storage/identity/network/ticket/detection/other, `ingest(assets)->int`,
async `sync() -> SyncResult` (success/partial/failed), `check_health()->bool`,
`describe_config()/describe_credentials()` JSON schemas. Contract tests
implement the §25 testing matrix + §26 minimum contract test verbatim.

## Wiring in real modules

1. Update `TARGET_MODULES` in `tests/conftest.py` with the real import paths.
2. Real connectors appear in `tests/contract/test_connector_contract.py::all_connectors()`.
3. Skips disappear automatically as modules land — no test edits needed.
