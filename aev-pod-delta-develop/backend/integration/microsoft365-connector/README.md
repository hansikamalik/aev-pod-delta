# Microsoft 365 Connector

Part of **AEV Platform — Pod Delta (M4)**, Integration squad.
This is the **Week 3** connector — the second one built on this project,
following the Google Workspace connector shipped in Weeks 1–2.

## What it does

Discovers identity, device, domain, and license assets from a Microsoft 365 /
Entra ID tenant via the Microsoft Graph API, normalizes them into the
platform's shared Asset shape, and pushes them to the asset/exposure service.

| Stage | Module | What it does |
|---|---|---|
| Authenticate | `auth.py` | OAuth2 client-credentials flow against Azure AD → app-only Graph token |
| Credentials | `credentials.py` | Pulls the app's client secret + platform API token from Vault |
| Discover / ingest | `discovery.py` | Pages through Graph API: users, groups, devices, domains, license SKUs, **directory audit logs** |
| Normalize | `normalization.py` | Maps users/groups/devices/domains/licenses → the shared `Asset` shape; audit log entries → the shared `Finding` shape |
| Push | `push.py` | Batches and posts assets to the assets ingest endpoint, findings to the findings ingest endpoint |
| Health check | `connector.py` | Verifies token validity + platform reachability |
| Orchestration | `connector.py` (`run_sync`) | authenticate → discover → ingest → normalize → push |

Audit log entries are events, not persistent resources, so they come out of
normalization as `Finding` objects (see `models.py`) instead of `Asset`
objects, and push to a separate `findings` endpoint on the platform API.
**Acceptance criterion this was built against: M365 users sync end-to-end**
(covered by `tests/test_integration.py::test_run_sync_acceptance_m365_users_synced`,
which runs discovery/normalization/push for users alone).

## Repo layout

```
microsoft365-connector/
├── README.md
├── WEEK3_TASK.md          ← the Week 3 task, broken down + checklist
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── conftest.py            ← sys.path setup (for pytest, once installed)
├── config/
│   └── config.example.yaml
├── docs/
│   ├── SETUP.md
│   └── CONFIG.md
├── src/microsoft365_connector/
│   ├── __init__.py
│   ├── base.py            ← stand-in Connector ABC (6 methods)
│   ├── config.py
│   ├── credentials.py     ← Vault client
│   ├── auth.py            ← Graph API OAuth2
│   ├── discovery.py       ← Graph API discovery + pagination
│   ├── normalization.py
│   ├── push.py            ← platform ingest client
│   ├── connector.py       ← Microsoft365Connector, ties it together
│   ├── cli.py             ← `python -m microsoft365_connector.cli`
│   ├── exceptions.py
│   └── models.py          ← shared Asset shape
├── tests/
│   ├── fixtures.py
│   ├── sandbox/mock_graph_api.py   ← offline Graph API sandbox
│   ├── test_auth.py
│   ├── test_discovery.py
│   ├── test_normalization.py
│   ├── test_push.py
│   └── test_integration.py
└── .github/workflows/ci.yml
```

## Setup

See `docs/SETUP.md` for Azure AD app registration, Graph permissions, and
Vault paths.

## Configuration

See `docs/CONFIG.md`. Sample at `config/config.example.yaml`.

## Testing

Tests are stdlib `unittest.TestCase`, so they run with **zero installs** and
**zero network** — a local sandbox (`tests/sandbox/`) fakes the Graph API:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py" -v
```

The same tests also run under pytest once `requirements-dev.txt` is
installed (pytest collects `unittest.TestCase` classes natively):

```bash
pip install -r requirements-dev.txt && pytest
```

## Assumptions to verify before merging

This was scaffolded without access to the shared `connector_sdk` package,
the platform's real ingest API contract, or the squad's actual Vault
wiring. Three integration points to double-check:

1. **`base.py`** — stand-in for the shared `Connector` ABC (authenticate,
   discover, ingest, normalize, push, health_check). Swap for
   `from connector_sdk.base import Connector` once confirmed the method
   signatures match Likith's TS/Python interface.
2. **`credentials.py`** — `VaultClient` assumes Vault's KV v2 HTTP API.
   Point it at the real Vault wiring the other connectors already use
   instead of the placeholder path convention here.
3. **`models.py`** — `Asset` fields are a best guess at the shared
   Asset/finding shape from the sprint plan. Align with whatever schema
   Normalization/AI Context actually ship.

## Week 3 task

See `WEEK3_TASK.md`.
