"""Connector configuration model.

`config` is the non-secret JSON blob stored on the `integrations` table
(see integrations.config JSONB). `credentials_ref` on that same table
points at the Vault path holding the actual client secret — it is never
present here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class DefenderConfig(BaseModel):
    tenant_id: str = Field(..., description="Azure AD tenant ID")
    client_id: str = Field(..., description="App registration (client) ID")
    api_base_url: HttpUrl = Field(
        default="https://api.securitycenter.microsoft.com",
        description="Microsoft Defender for Endpoint API base URL",
    )
    login_base_url: HttpUrl = Field(
        default="https://login.microsoftonline.com",
        description="Azure AD OAuth token endpoint base URL",
    )
    poll_interval_minutes: int = Field(
        default=15, ge=5, description="How often sync() should be scheduled"
    )
    machine_page_size: int = Field(default=500, ge=1, le=1000)
    alert_lookback_hours: int = Field(
        default=24,
        ge=1,
        description="On first sync (no last_sync_at), how far back to pull alerts",
    )
    request_timeout_seconds: float = Field(default=30.0, gt=0)
