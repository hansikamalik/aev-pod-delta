"""
POST /connectors/custom -- Week 3 Connector SDK deliverable.

The route talks only to `ConnectorRegistry` and `ImageValidator`, both
Protocols. Today's app.py wires in the in-memory / format-only stubs so
this is fully demoable with zero real infrastructure. Swapping in real
implementations later means writing a new class in registry.py or
image_check.py and changing the two `Depends` factories below -- nothing
in this file's route logic needs to change.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from .image_check import FormatOnlySyntaxValidator, ImageValidator
from .registry import (
    ConnectorAlreadyRegistered,
    ConnectorNotFound,
    ConnectorRegistry,
    InMemoryConnectorRegistry,
)
from .schemas import ConnectorRecord, ConnectorRegistrationRequest

app = FastAPI(title="Connector Registration (demo)")

# ---- the two swap points -----------------------------------------------
# Real infra replaces the return value here, not the functions' signatures.

_registry = InMemoryConnectorRegistry()


def get_registry() -> ConnectorRegistry:
    return _registry


def get_image_validator() -> ImageValidator:
    return FormatOnlySyntaxValidator()


# ---- routes --------------------------------------------------------------

@app.post("/connectors/custom", response_model=ConnectorRecord, status_code=201)
async def register_connector(
    request: ConnectorRegistrationRequest,
    registry: ConnectorRegistry = Depends(get_registry),
    image_validator: ImageValidator = Depends(get_image_validator),
) -> ConnectorRecord:
    check = await image_validator.check(request.image)
    if not check.ok:
        raise HTTPException(status_code=422, detail=f"image check failed: {check.detail}")

    record = ConnectorRecord(
        name=request.name,
        image=request.image,
        config_schema=request.config_schema,
        credential_schema=request.credential_schema,
        image_check_status="ok" if check.ok else "failed",
    )

    try:
        return registry.register(record)
    except ConnectorAlreadyRegistered as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/connectors/custom", response_model=list[ConnectorRecord])
async def list_connectors(registry: ConnectorRegistry = Depends(get_registry)) -> list[ConnectorRecord]:
    return registry.list()


@app.get("/connectors/custom/{name}", response_model=ConnectorRecord)
async def get_connector(name: str, registry: ConnectorRegistry = Depends(get_registry)) -> ConnectorRecord:
    try:
        return registry.get(name)
    except ConnectorNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
