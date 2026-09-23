# Integration Service

AEV Platform — Integration Squad — Week 1 scaffold.

Owners (Week 1): Harshal Sahare & Bhavesh Kanekar (FastAPI skeleton, `/health`,
contract test, docs). Vatsal Thummar owns the Connector interface freeze.
Subramani owns the `integrations` / `sync_jobs` migrations (not in this scaffold yet).

## Setup

1. Create a virtual environment (recommended):
   ```
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy the environment file:
   ```
   cp .env.example .env
   ```
4. Run the service locally:
   ```
   uvicorn app.main:app --reload
   ```
5. Visit http://localhost:8000/health — should return:
   ```json
   {"status": "ok", "service": "integration-service"}
   ```
   Interactive API docs are auto-generated at http://localhost:8000/docs.

## Running tests

```
pytest
```

This runs:
- `tests/test_health.py` — confirms `/health` returns 200
- `tests/test_contract.py` — confirms a connector implementing the shared
  interface (`app/connector_interface.py`) can be discovered, synced, and
  health-checked end-to-end

## Connector Contract

`app/connector_interface.py` currently holds a **placeholder** version of the
shared Connector interface. The real, agreed-upon contract is owned jointly by
the Integration Squad (Vatsal Thummar) and the Connector SDK Squad (Sai Kumar
Dungala), and must be frozen by end of Week 1.

`tests/dummy_connector.py` is a fake connector (no real API calls, hardcoded
data) used purely to prove the interface works. Once the real interface is
frozen:

1. Replace `app/connector_interface.py` with the agreed version (or import
   it from the shared SDK package once that exists).
2. Re-run `pytest`. If `DummyConnector` still passes without changes, the
   contract is stable and safe for real connectors (AWS, Azure, GCP, etc.)
   to build against.

## Running with Docker

Instead of the manual venv setup above, you can run the whole service (plus a
Postgres database) with Docker Compose:

```
docker-compose up --build
```

This starts:
- `integration-service` — this FastAPI app, available at `http://localhost:8000`
- `postgres` — a Postgres 16 database, available at `localhost:5432`

Check it worked the same way as before:
```
curl http://localhost:8000/health
```

To stop everything:
```
docker-compose down
```

To stop and also wipe the database data:
```
docker-compose down -v
```

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/)
installed and running first.

## Project structure

```
integration-service/
├── app/
│   ├── main.py                 # FastAPI app entrypoint
│   ├── config.py               # env var loading
│   ├── connector_interface.py  # placeholder Connector contract
│   └── routes/
│       └── health.py           # GET /health
├── tests/
│   ├── dummy_connector.py      # fake connector for contract testing
│   ├── test_contract.py        # proves the interface works end-to-end
│   └── test_health.py          # proves /health returns 200
├── requirements.txt
├── .env.example
└── README.md
```

## Pushing to GitHub

This project is already a git repo with an initial commit. To push it to a
new GitHub repo:

1. Create an empty repo on GitHub (don't initialize it with a README/license —
   this project already has one).
2. Point your local repo at it and push:
   ```
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git branch -M main
   git push -u origin main
   ```
3. For subsequent changes:
   ```
   git add .
   git commit -m "your message"
   git push
   ```

`.gitignore` is already set up to exclude `venv/`, `__pycache__/`, `.env`,
and other local-only files - so none of that gets pushed by accident.

## Week 1 checklist status

- [x] Service scaffold runs locally without errors
- [x] `/health` passes
- [x] Contract test passes against dummy connector
- [x] README written
- [ ] Connector interface contract agreed w/ SDK squad (blocks replacing the
      placeholder — owned by Vatsal + Sai Kumar)
- [ ] Merged to `main` via reviewed PR
