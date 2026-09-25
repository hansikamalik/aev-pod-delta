"""Runnable local app for the Webhook connector.

    uvicorn examples.app:app --reload --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from aev_connectors.webhook import routes
from aev_connectors.webhook.config import WebhookConfig
from aev_connectors.webhook.connector import WebhookConnector

logging.basicConfig(level=logging.INFO)


class LoggingPlatformClient:
    """Stand-in for Beta's asset/exposure service during local development."""

    async def upsert_assets(self, org_id: str, assets) -> None:
        logging.info("upsert %s asset(s) for %s", len(assets), org_id)

    async def upsert_findings(self, org_id: str, findings) -> None:
        logging.info("upsert %s finding(s) for %s", len(findings), org_id)


def create_app() -> FastAPI:
    config = WebhookConfig.from_env(org_id="org_local")
    connector = WebhookConnector(config, platform_client=LoggingPlatformClient())
    routes.configure(connector)

    application = FastAPI(title="AEV Webhook Connector", version=connector.version)
    application.include_router(routes.router)
    return application


app = create_app()
