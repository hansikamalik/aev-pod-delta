# gitlab-connector

GitLab connector for the AEV Platform — Pod Delta (M4).

**Squad:** Integration · **Owner:** Bhavesh Kanekar
**Sprint:** Week 3, Sep 18–Sep 24 · Sprint backlog item: "GitLab (full)", P0, 5 days

## Structure

```
connector-gitlab/
├── README.md
├── requirements.txt
├── pyproject.toml
├── docs/setup.md
├── src/gitlab_connector/
│   ├── base.py           # Connector ABC + Asset/Finding/SyncResult (stub of shared SDK)
│   ├── auth.py           # PRIVATE-TOKEN auth (gitlab.com or self-managed) + validation
│   ├── credentials.py    # Vault-backed credential loading
│   ├── discovery.py      # group projects (incl. subgroups) + per-project vulnerabilities
│   ├── normalization.py  # projects -> Asset, vulnerabilities -> Finding
│   ├── push.py           # bulk push to Beta's asset/exposure service
│   └── connector.py      # GitLabConnector — ties the pipeline together
└── tests/                # 37 tests, all mocked (no live API calls)
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

See [`docs/setup.md`](docs/setup.md) for Vault config, token scopes and the
three stubs to swap before staging.
