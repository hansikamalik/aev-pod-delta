# Connector SDK Guide — Start Here

Welcome to the AEV Pod Delta Connector SDK. This guide is for developers who are new to the repository and want to understand the contract, build a connector, run tests, package it, or register a custom connector.

> **How to use this guide:** Choose your goal from the table below, open the linked files, and follow the steps in order. File links are relative to the repository root so they open directly in GitHub. If a link is broken after the repository structure changes, search for the filename in GitHub and update this guide in the same pull request.

## Choose your task

| I want to… | Start here | Then open |
|---|---|---|
| Understand the SDK contract | [Python SDK package](backend/connector-sdk/connector_sdk/) | [Connector interface](backend/connector-sdk/connector_sdk/connector.py), [models](backend/connector-sdk/connector_sdk/models.py) |
| See a minimal connector | [Sample connector](backend/connector-sdk/connector_sdk/sample_connector.py) | [Sample connector tests](backend/connector-sdk/tests/test_sample_connector.py) |
| Build a Python connector | [Connector interface](backend/connector-sdk/connector_sdk/connector.py) | [Models](backend/connector-sdk/connector_sdk/models.py), [sample connector](backend/connector-sdk/connector_sdk/sample_connector.py), and the tests beside the SDK |
| Build a TypeScript connector | [TypeScript sandbox](backend/connector-sdk/connector_sandbox/ts/) | Find `connector.ts`, `models.ts`, `sampleConnector.ts`, and the corresponding tests in that folder |
| Run the Python sandbox | [Python sandbox](backend/connector-sdk/connector_sandbox/python/) | [Runner](backend/connector-sdk/connector_sandbox/python/sandbox/runner.py), [scenario configuration](backend/connector-sdk/connector_sandbox/python/scenarios/scenarios.yaml), [mock server](backend/connector-sdk/connector_sandbox/python/mock_server/server.py) |
| Understand sandbox scenarios | [Scenario definitions](backend/connector-sdk/connector_sandbox/python/scenarios/scenarios.yaml) | [Scenario loader](backend/connector-sdk/connector_sandbox/python/scenarios/scenario_loader.py), [reference connector](backend/connector-sdk/connector_sandbox/python/connectors/reference/connector.py) |
| Run tests | [Python SDK tests](backend/connector-sdk/tests/) | [Sandbox tests](backend/connector-sdk/connector_sandbox/python/tests/) |
| Understand custom registration | [Registration app](backend/connector-sdk/connector_sandbox/python/registration/app.py) | [Request/response schemas](backend/connector-sdk/connector_sandbox/python/registration/schemas.py), [schema rules](backend/connector-sdk/connector_sandbox/python/registration/schema_rules.py) |
| Understand image validation and scanning | [Image policy](backend/connector-sdk/connector_sandbox/python/registration/image_policy.py) | [Image validation](backend/connector-sdk/connector_sandbox/python/registration/image_check.py), [registration tests](backend/connector-sdk/connector_sandbox/python/tests/test_registration.py) |
| Review registration security and known gaps | [Security notes](backend/connector-sdk/connector_sandbox/docs/registration-hardening/REGISTRATION_SECURITY.md) | [Readiness](backend/connector-sdk/connector_sandbox/docs/registration-hardening/REGISTRATION_READINESS.md), [known gaps](backend/connector-sdk/connector_sandbox/docs/registration-hardening/KNOWN_GAPS.md), [handover](backend/connector-sdk/connector_sandbox/docs/registration-hardening/REGISTRATION_HANDOVER.md) |
| Verify Docker packaging | [Docker verification script](backend/connector-sdk/connector_sandbox/verify_docker.ps1) | [TypeScript Dockerfile](backend/connector-sdk/connector_sandbox/ts/Dockerfile) |

## 1. What is a connector?

A connector reads data from an external product—such as a cloud platform, SIEM, identity provider, ticketing system, or code repository—and maps that data into the platform's shared asset format. The shared SDK contract gives connectors a consistent shape so the integration layer can use them in a predictable way.

Before writing code, read the interface and models first. Do not copy a connector from another branch or an old example until you have checked that its method signatures and model fields match the current SDK in this repository.

## 2. Learn the contract before implementing it

Open these files in order:

1. [Connector interface](backend/connector-sdk/connector_sdk/connector.py) — understand both `Connector` and `AsyncConnector` lifecycle methods (`discover`, `ingest`, `sync`, `async_sync`).
2. [Shared models](backend/connector-sdk/connector_sdk/models.py) — understand `Asset` (with dual `discovered_at` / `discoveredAt` properties), `AssetType`, and `SyncResult` (with `records_synced` and `success` aliases).
3. [Domain exceptions](backend/connector-sdk/connector_sdk/exceptions.py) — use standardized exception types (`ConnectorError`, `AuthenticationError`, `ValidationError`).
4. [Sample connector](backend/connector-sdk/connector_sdk/sample_connector.py) — follow the reference working example.
5. [Sample connector tests](backend/connector-sdk/tests/test_sample_connector.py) — learn what behavior the tests expect.
6. [Canonical reconciliation tests](backend/connector-sdk/tests/test_canonical_reconciliation.py) — see async and sync verification under v1.0.0.

When implementing a connector, pay attention to:

- **Asynchronous & Synchronous support:** You can inherit from `AsyncConnector` for pure `async def discover()` / `async def ingest()`, or standard `Connector`. The SDK bridges both automatically.
- **Discovery:** read from the vendor API and normalize returned resources into the SDK's asset model. Both snake_case and camelCase attributes are fully supported.
- **Ingestion:** pass normalized assets to the platform-facing ingestion implementation.
- **Synchronization:** `sync()` and `async_sync()` coordinate discover -> ingest -> status derivation.
- **Health checks:** implement `check_health()` (or `health_check()`).
- **Configuration and credentials:** describe required settings clearly via `describe_config()` / `describe_credentials()` (or `get_config_schema()` / `get_credential_schema()`).
- **Failure behavior:** use timeouts for network calls and throw structured `ConnectorError` subclasses.

The Python and TypeScript SDKs are intended to follow the same contract, but verify their current implementations side by side rather than assuming every method or field is automatically kept in parity.

## 3. Build a connector step by step

1. **Choose the language.** Use the Python package or TypeScript SDK as the starting point.
2. **Read the interface and models.** Record required method signatures and model fields before coding.
3. **Copy the sample pattern.** Create a new connector class/module without modifying the shared contract unless the SDK team has agreed to a contract change.
4. **Implement vendor access.** Keep authentication, HTTP/API calls, pagination, response validation, and normalization clear and separately testable.
5. **Normalize data.** Return the SDK's asset model; preserve the original vendor payload when the model supports it.
6. **Describe configuration and credentials.** Include required fields and ensure secrets are marked correctly.
7. **Add tests.** Cover success, empty results, malformed responses, authentication/authorization errors, rate limiting, server errors, timeouts, health checks, and ingestion failures as applicable.
8. **Run the tests locally.** Use the test commands documented in the package's README or project configuration. Run commands from the relevant package directory.
9. **Review compatibility.** Compare the new connector with the interface, shared models, and reference tests before opening a pull request.

> **Important:** This guide explains the workflow, not a substitute for the live contract. The interface and model files in the current branch are authoritative if an example elsewhere disagrees.

## 4. Run the Python sandbox

The sandbox lets you exercise a reference connector against a mock API and scenario-driven responses without connecting to a real vendor account.

Open the [Python sandbox folder](backend/connector-sdk/connector_sandbox/python/) and inspect:

- `sandbox/runner.py` — starts a connector scenario and reports its outcome.
- `scenarios/scenarios.yaml` — lists the configured scenarios.
- `scenarios/scenario_loader.py` — loads scenario definitions.
- `mock_server/server.py` — serves simulated API responses.
- `connectors/reference/connector.py` — reference implementation used by the harness.
- `tests/` — tests for the sandbox and reference connector.

From the Python sandbox project directory, create and activate a virtual environment if the project instructions require one, install the dependencies specified by its project configuration, and run the tests with `python -m pytest`. Use the sandbox's own README or `pyproject.toml` for exact setup commands; do not assume the SDK package and sandbox share the same dependencies or working directory.

The repository has previously been exercised with the `success`, `unauthorized`, `forbidden`, and `rate_limited` mock scenarios. Re-run the current tests before relying on those outcomes after changing the code.

## 5. Test the custom registration service

The custom registration API is implemented under [`registration/`](backend/connector-sdk/connector_sandbox/python/registration/).

Read the files in this order:

1. [`app.py`](backend/connector-sdk/connector_sandbox/python/registration/app.py) — routes and request flow.
2. [`schemas.py`](backend/connector-sdk/connector_sandbox/python/registration/schemas.py) — request/response shapes.
3. [`schema_rules.py`](backend/connector-sdk/connector_sandbox/python/registration/schema_rules.py) — schema validation rules.
4. [`image_policy.py`](backend/connector-sdk/connector_sandbox/python/registration/image_policy.py) — allowed-registry and image-reference policy.
5. [`image_check.py`](backend/connector-sdk/connector_sandbox/python/registration/image_check.py) — scanner integration and result handling.
6. [`test_registration.py`](backend/connector-sdk/connector_sandbox/python/tests/test_registration.py), [`test_schema_rules.py`](backend/connector-sdk/connector_sandbox/python/tests/test_schema_rules.py), and [`test_image_policy.py`](backend/connector-sdk/connector_sandbox/python/tests/test_image_policy.py) — expected behavior and regression coverage.

The intended workflow is to submit a connector name, image reference, and configuration/credential schemas to `POST /connectors/custom`. Read `app.py` and the schemas for the exact request shape and status codes in the branch you are using.

The current implementation uses image-policy validation and a Trivy-based scan. A successful scan is not a guarantee that an image is safe in every deployment environment. Before exposing registration publicly, review the security notes, registry allowlist configuration, scanner isolation/egress controls, and the documented known gaps.

## 6. Package and verify

Use the repository's actual Dockerfile and verification script rather than inventing a new build command:

- [Docker verification script](backend/connector-sdk/connector_sandbox/verify_docker.ps1)
- [TypeScript sandbox Dockerfile](backend/connector-sdk/connector_sandbox/ts/Dockerfile)

Read the script before running it so you know what it builds, which tests it executes, and what it expects to be installed. Run it from the directory specified in the script or its README. A successful local packaging check proves only the checks that the script performs; it does not by itself establish production readiness.

## 7. Python Wheel Distribution & Installation

The SDK is packaged as the canonical `aev-connector-sdk` Python wheel:

### Building the Wheel
```bash
# From repository root or backend/connector-sdk/
cd backend/connector-sdk
python3 -m pip install build
python3 -m build
```
This generates the source distribution and `.whl` binary artifact in `backend/connector-sdk/dist/`:
- `dist/aev_connector_sdk-1.0.0-py3-none-any.whl`
- `dist/aev_connector_sdk-1.0.0.tar.gz`

### Installing in Services
Any downstream service or connector package can install the wheel directly:
```bash
# Production installation from built wheel
pip install backend/connector-sdk/dist/aev_connector_sdk-1.0.0-py3-none-any.whl

# Editable local development mode
pip install -e backend/connector-sdk
```

The package includes `py.typed` for PEP 561 compliant static type checking with `mypy` or `pyright`.


