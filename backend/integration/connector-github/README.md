# github-connector

GitHub connector for the AEV Platform — Pod Delta (M4).

**Squad:** Integration · **Owner:** Bhavesh Kanekar
**Sprint:** Week 2, Sep 11–Sep 17 · Sprint backlog item: "GitHub (full)", P0, 5 days

## Structure

```
connector-github/
├── README.md
├── requirements.txt
├── pyproject.toml
├── docs/setup.md
├── src/github_connector/
│   ├── base.py           # Connector ABC + Asset/Finding/SyncResult (stub of shared SDK)
│   ├── auth.py           # Bearer-token auth (github.com or GitHub Enterprise) + validation
│   ├── credentials.py    # Vault-backed credential loading
│   ├── discovery.py      # repos + Dependabot/code-scanning/secret-scanning alerts
│   ├── normalization.py  # repos -> Asset, alerts -> Finding
│   ├── push.py           # bulk push to Beta's asset/exposure service
│   └── connector.py      # GitHubConnector — ties the pipeline together
└── tests/                # 38 tests, all mocked (no live API calls)
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
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate.bat
pip install -r requirements.txt
pytest tests/ -v
```

See [`docs/setup.md`](docs/setup.md) for Vault config, token permissions and the
three stubs to swap before staging.
