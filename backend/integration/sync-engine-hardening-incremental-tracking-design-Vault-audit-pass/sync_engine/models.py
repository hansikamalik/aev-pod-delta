from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator
from sync_engine.vault_audit import SENSITIVE_AUDIT_KEYS


class HealthCheckResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    connector_id: str = Field(alias="connector")
    healthy: bool
    latency_ms: float
    message: str = "OK"
    vault_audit_passed: bool = True

    @model_validator(mode="before")
    @classmethod
    def accept_connector_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "connector" in data and "connector_id" not in data:
                data["connector_id"] = data["connector"]
            elif "connector_id" in data and "connector" not in data:
                data["connector"] = data["connector_id"]
        return data


class Checkpoint(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    connector_id: str = Field(alias="connector")
    high_water_mark: datetime = Field(alias="hwm")

    @model_validator(mode="before")
    @classmethod
    def accept_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "connector_id" in data and "connector" not in data:
                data["connector"] = data["connector_id"]
            elif "connector" in data and "connector_id" not in data:
                data["connector_id"] = data["connector"]

            if "high_water_mark" in data and "hwm" not in data:
                data["hwm"] = data["high_water_mark"]
            elif "hwm" in data and "high_water_mark" not in data:
                data["high_water_mark"] = data["hwm"]
        return data


class Asset(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    asset_id: str = Field(alias="id")
    raw: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = Field(default=None, alias="ts")

    @model_validator(mode="before")
    @classmethod
    def accept_asset_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "asset_id" in data and "id" not in data:
                data["id"] = str(data["asset_id"])
            elif "id" in data and "asset_id" not in data:
                data["asset_id"] = str(data["id"])

            if "timestamp" in data and "ts" not in data:
                data["ts"] = data["timestamp"]
            elif "ts" in data and "timestamp" not in data:
                data["timestamp"] = data["ts"]
        return data


class SyncResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    assets_pushed: int
    high_water_mark: str
    errors: List[str] = Field(default_factory=list)
    vault_audit_passed: bool = True
