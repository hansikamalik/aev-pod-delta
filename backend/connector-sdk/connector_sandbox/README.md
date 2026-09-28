# Connector Sandbox

A local test environment for connectors. It gives a connector a **fake vendor API** to talk to, so
you can test success, empty, malformed, error and timeout behaviour with no real credentials and no
real network calls.

It has two halves that ship together and are run with one command:

| Half | Contains | Tests |
|---|---|---|
| [`python/`](python) | FastAPI mock server, 8 switchable scenarios, reference connector, CLI runner, vendored Python SDK | pytest |
| [`ts/`](ts) | TypeScript SDK (zod), reusable contract suite, in-process mock server, sample connector | vitest |

> **Which SDK?** The sandbox vendors the *Week-1* SDK (`python/connector_sdk`, `ts/src`). The
> `connector-sdk-v0.1.0` in the `aev-pod-delta` repo differs (async `sync()`, different field names).
> See [docs/KNOWN_GAPS.md](docs/KNOWN_GAPS.md) before onboarding a connector written for that SDK.

## Quick start

Prerequisites: Python 3.12+, Node 20+, network access on first run (to install packages).

```powershell
.\run_all.ps1              # Python tests, then TS typecheck + tests
.\run_all.ps1 -PythonOnly
.\run_all.ps1 -TsOnly
.\run_all.ps1 -Serve       # start the mock server on http://127.0.0.1:8080
```

If PowerShell blocks the script: `Set-ExecutionPolicy -Scope Process Bypass`.
macOS / Linux / Git Bash: `./run_all.sh [--python-only | --ts-only | --serve]`.

A green run ends with `python pytest PASS`, `ts typecheck PASS`, `ts vitest PASS`.

## Try it by hand

Two terminals, from `python/` with the venv active (`run_all.ps1` creates `python/.venv`):

```powershell
uvicorn mock_server.server:app --port 8080             # terminal 1
python -m sandbox.runner --scenario success             # terminal 2  -> exit code 0
python -m sandbox.runner --scenario server_error        #             -> exit code 1
```

Or open `http://127.0.0.1:8080/api/assets?scenario=unauthorized` in a browser.

## Layout

```
connector-sandbox/
├── README.md
├── run_all.ps1 / run_all.sh
├── docs/                        detailed documentation (see below)
├── python/
│   ├── mock_server/             GET /health, GET /api/assets?scenario=<name>
│   ├── scenarios/               scenarios.yaml + loader
│   ├── connector_sdk/           vendored Python SDK
│   ├── connectors/reference/    example HTTP connector
│   ├── sandbox/runner.py        CLI
│   ├── conftest.py              test fixtures
│   └── tests/
└── ts/
    ├── src/                     SDK: connector.ts, models.ts, sampleConnector.ts
    ├── src/testing/             runContractSuite, MockApiServer, mock data
    ├── tests/
    └── docs/CONNECTOR_GUIDE.md  TypeScript connector guide
```

## Documentation

| Read this | If you want to |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | understand how the pieces fit and what `sync()` does |
| [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | write and test a new Python connector |
| [ts/docs/CONNECTOR_GUIDE.md](ts/docs/CONNECTOR_GUIDE.md) | write and test a new TypeScript connector |
| [docs/SCENARIOS.md](docs/SCENARIOS.md) | see what each scenario does, or add one |
| [docs/TESTING.md](docs/TESTING.md) | understand the test suites, fixtures and expected behaviour |
| [docs/KNOWN_GAPS.md](docs/KNOWN_GAPS.md) | know what the sandbox does **not** do yet, and open decisions |
| [docs/STATUS_REPORT.md](docs/STATUS_REPORT.md) | see the dated verification results and checklist scorecard |

