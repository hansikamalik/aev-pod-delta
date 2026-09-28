import time

from fastapi import FastAPI, HTTPException, Query

from scenarios.scenario_loader import load_scenarios


app = FastAPI(title="Connector Sandbox Mock Server")

_SUCCESS_ASSETS = [
    {
        "id": "asset-001",
        "name": "reference-server-01",
        "type": "compute",
        "status": "active",
    },
    {
        "id": "asset-002",
        "name": "reference-server-02",
        "type": "compute",
        "status": "active",
    },
]


_MALFORMED_ASSETS = [
    {"id": "asset-broken"},
    {"id": "asset-bad-type", "name": "weird one", "type": "spaceship"},
]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/assets")
def get_assets(
    scenario: str = Query(default="success"),
):
    scenarios = load_scenarios()

    if scenario not in scenarios:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario: {scenario}",
        )

    config = scenarios[scenario]
    status_code = config["status_code"]

    delay = config.get("delay_seconds")
    if delay:
        time.sleep(delay)

    if status_code != 200:
        raise HTTPException(
            status_code=status_code,
            detail=scenario,
        )

    if scenario == "empty":
        return {"assets": []}

    if scenario == "malformed":
        return {"assets": _MALFORMED_ASSETS}

    return {"assets": _SUCCESS_ASSETS}