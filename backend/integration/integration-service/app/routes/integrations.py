"""
FastAPI Router for Integration Management REST Endpoints.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status

from app.locking import sync_lock_manager
from app.models import (
    CatalogItem,
    HealthCheckResponse,
    HealthStatus,
    IntegrationCreate,
    IntegrationResponse,
    IntegrationUpdate,
    SyncCheckpoint,
    SyncJobResponse,
    SyncJobStatus,
)
from app.registry import ConnectorRegistry
from app.storage import storage

router = APIRouter()


# ---- 1. Catalog Endpoints ---------------------------------------------------

@router.get("/catalog", response_model=List[CatalogItem], summary="List supported connectors")
def list_catalog():
    """Returns the catalog of all supported enterprise connectors with their
    configuration and credential JSON schemas.
    """
    return ConnectorRegistry.get_catalog()


# ---- 2. Integration CRUD Endpoints ------------------------------------------

@router.post(
    "",
    response_model=IntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new integration connector",
)
def create_integration(payload: IntegrationCreate):
    """Register and configure a new connector instance.
    Validates connector type against the catalog and stores configurations.
    """
    supported = ConnectorRegistry.get_supported_types()
    if payload.connector_type not in supported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported connector type '{payload.connector_type}'. Must be one of: {supported}",
        )

    integration = storage.create(payload)
    return integration


@router.get("", response_model=List[IntegrationResponse], summary="List all configured integrations")
def list_integrations(
    connector_type: Optional[str] = Query(None, description="Filter by connector type"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
):
    """Returns all registered connectors. Sensitive credentials are automatically masked."""
    return storage.list_all(connector_type=connector_type, enabled=enabled)


@router.get("/{integration_id}", response_model=IntegrationResponse, summary="Get integration details")
def get_integration(integration_id: str):
    """Retrieve configuration and status details for a specific integration."""
    integration = storage.get(integration_id)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_id}' not found",
        )
    return integration


@router.put("/{integration_id}", response_model=IntegrationResponse, summary="Update integration")
def update_integration(integration_id: str, payload: IntegrationUpdate):
    """Update non-secret configuration or rotate credentials for an integration."""
    updated = storage.update(integration_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_id}' not found",
        )
    return updated


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete integration")
def delete_integration(integration_id: str):
    """Remove a configured integration from the platform."""
    deleted = storage.delete(integration_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_id}' not found",
        )
    return None


# ---- 3. Operational Endpoints (Health Check & Sync) -------------------------

@router.post("/{integration_id}/test", response_model=HealthCheckResponse, summary="Test connector health")
def test_integration_health(integration_id: str):
    """Run an on-demand health check against the external vendor API."""
    record = storage.get_record(integration_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_id}' not found",
        )

    try:
        connector = ConnectorRegistry.instantiate(
            connector_type=record.connector_type,
            config=record.config,
            credentials=record.credentials,
        )
        healthy = ConnectorRegistry.test_health(connector)
    except Exception as exc:
        healthy = False

    storage.update_health(integration_id, healthy)

    return HealthCheckResponse(
        integration_id=integration_id,
        connector_type=record.connector_type,
        healthy=healthy,
        status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
        checked_at=datetime.now(timezone.utc),
        message="Credentials verified and endpoint reachable" if healthy else "Health check failed to reach endpoint",
    )


@router.post("/{integration_id}/sync", response_model=SyncJobResponse, summary="Trigger manual sync")
def trigger_sync(integration_id: str):
    """Execute an immediate discover-and-ingest synchronization cycle.
    Records job results and discovered asset metrics into history.
    """
    record = storage.get_record(integration_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_id}' not found",
        )

    if not record.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integration '{integration_id}' is disabled. Enable it before triggering sync.",
        )

    job_id = f"job-{uuid4().hex[:8]}"

    # P1-2: Distributed lock acquisition to prevent concurrent execution on the same connector
    if not sync_lock_manager.acquire_lock(integration_id, job_id, ttl_seconds=300):
        active_job = sync_lock_manager.get_active_job(integration_id) or "in_progress"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "sync_in_progress",
                "message": f"A synchronization job is already running for integration '{integration_id}'",
                "job_id": active_job,
                "integration_id": integration_id,
            },
        )

    started_at = datetime.now(timezone.utc)
    t0 = time.time()

    try:
        connector = ConnectorRegistry.instantiate(
            connector_type=record.connector_type,
            config=record.config,
            credentials=record.credentials,
        )
        sync_status, discovered, pushed, errors = ConnectorRegistry.execute_sync(connector)
        job_status = SyncJobStatus.SUCCESS if sync_status == "success" else SyncJobStatus.FAILED
    except Exception as exc:
        job_status = SyncJobStatus.FAILED
        discovered = 0
        pushed = 0
        errors = [str(exc)]
    finally:
        # P1-2: Always release distributed lock when execution finishes
        sync_lock_manager.release_lock(integration_id, job_id)

    duration = round(time.time() - t0, 4)
    finished_at = datetime.now(timezone.utc)

    # Persist job record
    job_record = SyncJobResponse(
        job_id=job_id,
        integration_id=integration_id,
        connector_type=record.connector_type,
        status=job_status,
        assets_discovered=discovered,
        assets_pushed=pushed,
        errors=errors,
        duration_seconds=duration,
        started_at=started_at,
        finished_at=finished_at,
    )
    storage.record_job(job_record)
    storage.update_sync_results(integration_id, job_status.value, discovered)

    # P1-2: Record persistent sync checkpoint with high-watermark cursor
    checkpoint = SyncCheckpoint(
        integration_id=integration_id,
        last_sync_time=finished_at,
        last_cursor=f"cursor-{int(finished_at.timestamp())}-{job_id}",
        status=job_status.value,
        assets_discovered=discovered,
        assets_pushed=pushed,
        updated_at=finished_at,
    )
    storage.record_checkpoint(checkpoint)

    return job_record


@router.get("/{integration_id}/checkpoint", response_model=SyncCheckpoint, summary="Get sync checkpoint")
def get_sync_checkpoint(integration_id: str):
    """Retrieve the latest incremental synchronization checkpoint and high-watermark cursor."""
    record = storage.get_record(integration_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_id}' not found",
        )

    checkpoint = storage.get_checkpoint(integration_id)
    if not checkpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No sync checkpoint exists yet for integration '{integration_id}'",
        )
    return checkpoint


@router.patch("/{integration_id}/enable", response_model=IntegrationResponse, summary="Enable integration")
def enable_integration(integration_id: str):
    """Enable sync schedules and operational checks for an integration."""
    updated = storage.update(integration_id, IntegrationUpdate(enabled=True))
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_id}' not found",
        )
    return updated


@router.patch("/{integration_id}/disable", response_model=IntegrationResponse, summary="Disable integration")
def disable_integration(integration_id: str):
    """Pause sync schedules and disable manual sync execution."""
    updated = storage.update(integration_id, IntegrationUpdate(enabled=False))
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_id}' not found",
        )
    return updated


# ---- 4. History & Jobs Endpoints --------------------------------------------

@router.get(
    "/{integration_id}/history",
    response_model=List[SyncJobResponse],
    summary="Get execution history for integration",
)
def get_sync_history(
    integration_id: str,
    limit: int = Query(50, ge=1, le=200, description="Max jobs to return"),
):
    """Returns past synchronization job logs and metric trends for a specific connector."""
    record = storage.get(integration_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration '{integration_id}' not found",
        )
    return storage.get_jobs_for_integration(integration_id, limit=limit)


@router.get("/jobs/all", response_model=List[SyncJobResponse], summary="List all platform sync jobs")
def list_all_jobs(limit: int = Query(100, ge=1, le=500)):
    """Returns chronological sync runs across all active connectors."""
    return storage.list_all_jobs(limit=limit)
