"""FastAPI routes for the custom Webhook connector.

Mounted by the integration service at `/connectors/webhook`.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, HttpUrl

from .auth import AuthError
from .connector import WebhookConnector
from .models import DeliveryStatus, Event
from .subscriptions import SubscriptionError

router = APIRouter(prefix="/connectors/webhook", tags=["webhook"])

_connector: WebhookConnector | None = None


def configure(connector: WebhookConnector) -> None:
    """Called once at app startup by the integration service."""
    global _connector
    _connector = connector


def get_connector() -> WebhookConnector:
    if _connector is None:
        raise HTTPException(status_code=503, detail="webhook connector not configured")
    return _connector


class SubscriptionCreate(BaseModel):
    target_url: HttpUrl
    event_types: list[str] = Field(min_length=1)


class SubscriptionUpdate(BaseModel):
    event_types: list[str] | None = None
    active: bool | None = None


class EmitRequest(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("/health")
async def health(connector: WebhookConnector = Depends(get_connector)) -> dict[str, Any]:
    return await connector.health_check()


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def receive_event(
    request: Request,
    connector: WebhookConnector = Depends(get_connector),
) -> dict[str, Any]:
    """Inbound endpoint: an external system POSTs a signed event here."""
    body = await request.body()
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="body is not valid JSON") from exc

    try:
        buffered = connector.accept_inbound(body, dict(request.headers), payload)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"accepted": True, "records_buffered": buffered}


@router.post("/sync")
async def sync(connector: WebhookConnector = Depends(get_connector)) -> dict[str, Any]:
    """Drain buffered inbound events into the platform."""
    result = await connector.ingest()
    return result.model_dump(mode="json")


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    body: SubscriptionCreate,
    connector: WebhookConnector = Depends(get_connector),
) -> dict[str, Any]:
    try:
        sub = connector.subscribe(str(body.target_url), body.event_types)
    except SubscriptionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return sub.model_dump(mode="json")


@router.get("/subscriptions")
async def list_subscriptions(
    connector: WebhookConnector = Depends(get_connector),
) -> list[dict[str, Any]]:
    rows = connector.subscriptions.list(connector.config.org_id, connector.config.connector_id)
    return [r.model_dump(mode="json") for r in rows]


@router.patch("/subscriptions/{subscription_id}")
async def update_subscription(
    subscription_id: str,
    body: SubscriptionUpdate,
    connector: WebhookConnector = Depends(get_connector),
) -> dict[str, Any]:
    fields = body.model_dump(exclude_none=True)
    try:
        sub = connector.subscriptions.update(subscription_id, **fields)
    except SubscriptionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return sub.model_dump(mode="json")


@router.delete(
    "/subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_subscription(
    subscription_id: str,
    connector: WebhookConnector = Depends(get_connector),
) -> None:
    connector.unsubscribe(subscription_id)


@router.post("/emit")
async def emit(
    body: EmitRequest,
    connector: WebhookConnector = Depends(get_connector),
) -> list[dict[str, Any]]:
    """Fan an event out to every matching subscription (used by the sync engine)."""
    event = Event(
        org_id=connector.config.org_id,
        event_type=body.event_type,
        payload=body.payload,
    )
    records = await connector.emit(event)
    return [r.model_dump(mode="json") for r in records]


@router.get("/deliveries")
async def list_deliveries(
    status_filter: DeliveryStatus | None = None,
    limit: int = 100,
    connector: WebhookConnector = Depends(get_connector),
) -> list[dict[str, Any]]:
    rows = connector.delivery_log.list(connector.config.org_id, status_filter, limit)
    return [r.model_dump(mode="json") for r in rows]


@router.post("/deliveries/{delivery_id}/redeliver")
async def redeliver(
    delivery_id: str,
    connector: WebhookConnector = Depends(get_connector),
) -> dict[str, Any]:
    try:
        record = await connector.redeliver(delivery_id)
    except Exception as exc:  # noqa: BLE001 — mapped to a 404 for the caller
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return record.model_dump(mode="json")
