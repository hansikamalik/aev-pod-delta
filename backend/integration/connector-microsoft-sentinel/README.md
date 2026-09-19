# microsoft-sentinel-connector

Microsoft Sentinel connector for the AEV Platform — Pod Delta (M4).

**Squad:** Integration · **Owner:** Harshal Sahare (Lead)
**Sprint:** Week 1, Sep 4–Sep 10 · Sprint backlog item: "Microsoft Sentinel (full)", P0, 5 days

## Structure

```
connector-microsoft-sentinel/
├── README.md
├── requirements.txt
├── docs/
│   └── setup.md              # setup, config, and wiring TODOs
├── src/
│   └── sentinel_connector/
│       ├── __init__.py
│       ├── base.py           # Connector ABC + Asset/Finding/SyncResult shapes
│       ├── auth.py           # Azure AD OAuth2 client-credentials auth
│       ├── credentials.py    # Vault-backed credential loading
│       ├── discovery.py      # incident discovery + entity ingestion (ARM API)
│       ├── normalization.py  # incident/entity -> shared Asset/Finding shape
│       ├── push.py           # bulk push to Beta's asset/exposure service
│       └── connector.py      # SentinelConnector — ties the pipeline together
└── tests/
    ├── test_auth.py
    ├── test_credentials.py
    ├── test_discovery.py
    ├── test_normalization.py
    ├── test_push.py
    └── test_integration.py   # full pipeline test, mocked end-to-end
```

## Task breakdown (matches sprint plan)

| Task | Status | File(s) |
|---|---|---|
| Authentication | ✅ | `auth.py` |
| Credentials via Vault | ✅ | `credentials.py` |
| Discovery/ingestion | ✅ | `discovery.py` |
| Normalization | ✅ | `normalization.py` |
| Push to platform | ✅ | `push.py` |
| Unit + integration tests | ✅ | `tests/` |
| Documentation | ✅ | `docs/setup.md`, this file |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

See [`docs/setup.md`](docs/setup.md) for Vault config, required
credentials, and the three integration points that need to be wired
to your team's real shared packages (`connector_sdk`, Vault client,
Beta's asset-service client) before this goes to staging — this
scaffold ships with clearly marked stubs for each.

## Sandbox / real-API note

This connector currently calls the live Azure Resource Manager API
directly (`discovery.py`). Connector SDK's Python sandbox v2 (Week 2
deliverable) will let this — and every other connector — be tested
without hitting real vendor APIs. Once that lands, point the test
suite's `requests.Session` mocks at the sandbox harness instead.
