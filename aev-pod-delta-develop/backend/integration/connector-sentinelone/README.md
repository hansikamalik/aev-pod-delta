# sentinelone-connector

SentinelOne connector for the AEV Platform — Pod Delta (M4).

**Squad:** Integration · **Owner:** Bhavesh Kanekar
**Sprint:** Week 1, Sep 4–Sep 10 · Sprint backlog item: "SentinelOne (full) + Bhawook ramp-up", P0, 5 days

## Structure

```
connector-sentinelone/
├── README.md
├── requirements.txt
├── pyproject.toml
├── docs/
│   └── setup.md              # setup, config, wiring TODOs, ramp-up notes
├── src/sentinelone_connector/
│   ├── base.py               # Connector ABC + Asset/Finding/SyncResult (stub of shared SDK)
│   ├── auth.py               # ApiToken auth + token validation
│   ├── credentials.py        # Vault-backed credential loading
│   ├── discovery.py          # agent discovery + threat ingestion (cursor paging, 429 backoff)
│   ├── normalization.py      # agents -> Asset, threats -> Finding
│   ├── push.py               # bulk push to Beta's asset/exposure service
│   └── connector.py          # SentinelOneConnector — ties the pipeline together
└── tests/                    # 28 tests, all mocked (no live API calls)
```

## Task breakdown (matches sprint plan)

| Task | Status | File(s) |
|---|---|---|
| Authentication (1d) | ✅ | `auth.py` |
| Credentials via Vault (0.5d) | ✅ | `credentials.py` |
| Discovery/ingestion (1.5d) | ✅ | `discovery.py` |
| Normalization (0.5d) | ✅ | `normalization.py` |
| Push to platform (0.5d) | ✅ | `push.py` |
| Unit + integration tests (1d) | ✅ | `tests/` |
| Documentation (0.5d) | ✅ | `docs/setup.md`, this file |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

See [`docs/setup.md`](docs/setup.md) for Vault config and the three stubs
(`connector_sdk`, Vault client, Beta asset service) to swap before staging.
