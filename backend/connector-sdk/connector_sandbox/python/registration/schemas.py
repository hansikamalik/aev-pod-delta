"""
Request/response shapes for POST /connectors/custom.

Deliberately reuses the exact envelope Connector.describe_config() /
describe_credentials() already return: {type, properties, required}. If
this endpoint accepted a different shape, we'd have two competing schema
formats in the platform -- the one connectors already speak, and a second
one invented just for registration. See docs/REGISTRATION_READINESS.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

NAME_PATTERN = r"^[a-z][a-z0-9_]*$"  # matches the naming rule connector_sdk already enforces


class JsonSchemaEnvelope(BaseModel):
    """The exact shape describe_config()/describe_credentials() return.

    Kept as its own model (rather than dict[str, Any]) so "wrong shape
    submitted" is a 422 with a clear message, not a record silently
    stored with the wrong grammar -- which is exactly the bug we found
    in the TS connector guide (a flat field map instead of this envelope).
    """

    model_config = ConfigDict(extra="forbid")

    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class ConnectorRegistrationRequest(BaseModel):
    name: str
    image: str
    config_schema: JsonSchemaEnvelope
    credential_schema: JsonSchemaEnvelope

    @field_validator("name")
    @classmethod
    def name_matches_contract_rule(cls, v: str) -> str:
        import re

        if not re.fullmatch(NAME_PATTERN, v):
            raise ValueError(
                f"name must match {NAME_PATTERN!r} (lowercase letters, digits, "
                f"underscores, starting with a letter) -- got {v!r}"
            )
        return v

    @field_validator("image")
    @classmethod
    def image_is_a_plausible_reference(cls, v: str) -> str:
        # Format-only check. Whether the image actually exists and runs is
        # a separate concern -- see ImageValidator in image_check.py.
        if not v or " " in v or v.count(":") > 2:
            raise ValueError(f"not a plausible image reference: {v!r}")
        return v

    @field_validator("credential_schema")
    @classmethod
    def credentials_are_marked_secret(cls, v: JsonSchemaEnvelope) -> JsonSchemaEnvelope:
        for field_name, field_def in v.properties.items():
            if not isinstance(field_def, dict) or not field_def.get("secret"):
                raise ValueError(
                    f"credential_schema.properties.{field_name} must set "
                    f'"secret": true -- credential fields that aren\'t marked '
                    f"secret are a config-vs-credential mix-up"
                )
        return v


class ConnectorRecord(BaseModel):
    """What's actually stored, and what GET returns."""

    name: str
    image: str
    config_schema: JsonSchemaEnvelope
    credential_schema: JsonSchemaEnvelope
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    image_check_status: str = "unchecked"  # "unchecked" | "ok" | "failed" -- see image_check.py
