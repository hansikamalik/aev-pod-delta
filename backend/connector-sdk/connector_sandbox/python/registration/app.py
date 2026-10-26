"""
POST /connectors/custom -- Week 3 Connector SDK deliverable.

The route talks only to three Protocols: `ConnectorRegistry`, `ImageValidator`
and `ImageScanner`. Today's app.py wires in an in-memory registry, the
policy-based image validator (strict syntax, registry allowlist, pinned image)
and a placeholder scanner. Swapping in real implementations later means
writing a new class in registry.py or image_check.py and changing the
`Depends` factories below -- nothing in the route logic needs to change.

Configuration: set ALLOWED_REGISTRIES to a comma-separated list of registry
hosts (for example "registry.example.com,ghcr.io"). If it is unset, every
registration is rejected (default deny). See docs/REGISTRATION_SECURITY.md.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from .image_check import (
    SCAN_FAILED,
    SCAN_PASSED,
    ImageScanner,
    ImageValidator,
    PolicyImageValidator,
    TrivyDockerScanner,
)
from .image_policy import ImagePolicy
from .registry import (
    ConnectorAlreadyRegistered,
    ConnectorNotFound,
    ConnectorRegistry,
    InMemoryConnectorRegistry,
)
from .schemas import ConnectorRecord, ConnectorRegistrationRequest

app = FastAPI(title="Connector Registration (demo)")

# ---- the swap points ---------------------------------------------------
# Real infra replaces the return value here, not the functions' signatures.

_registry = InMemoryConnectorRegistry()


def get_registry() -> ConnectorRegistry:
    return _registry


def get_image_validator() -> ImageValidator:
    # Read per request so the allowlist can be changed without a restart in tests.
    return PolicyImageValidator(ImagePolicy.from_env())


def get_image_scanner() -> ImageScanner:
    return TrivyDockerScanner()


# ---- routes --------------------------------------------------------------

@app.post("/connectors/custom", response_model=ConnectorRecord, status_code=201)
async def register_connector(
    request: ConnectorRegistrationRequest,
    registry: ConnectorRegistry = Depends(get_registry),
    image_validator: ImageValidator = Depends(get_image_validator),
    image_scanner: ImageScanner = Depends(get_image_scanner),
) -> ConnectorRecord:
    check = await image_validator.check(request.image)
    if not check.ok:
        raise HTTPException(status_code=422, detail=f"image check failed: {check.detail}")

    scan = await image_scanner.scan(request.image)

    if scan.status == SCAN_FAILED:
        raise HTTPException(
            status_code=422,
            detail=f"image scan failed: {scan.detail}",
        )

    if scan.status != SCAN_PASSED:
        raise HTTPException(
            status_code=503,
            detail=f"image scan unavailable: {scan.detail}",
        )

    record = ConnectorRecord(
        name=request.name,
        image=request.image,
        config_schema=request.config_schema,
        credential_schema=request.credential_schema,
        image_check_status="ok",
        scan_status=scan.status,
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
