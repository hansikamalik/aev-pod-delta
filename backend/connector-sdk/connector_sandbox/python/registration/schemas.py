"""
Request/response shapes for POST /connectors/custom.

Deliberately reuses the exact envelope Connector.describe_config() /
describe_credentials() already return: {type, properties, required}. If
this endpoint accepted a different shape, we'd have two competing schema
formats in the platform -- the one connectors already speak, and a second
one invented just for registration. See docs/REGISTRATION_READINESS.md.

Security-relevant validation lives in two stdlib-only modules so it can be
tested without pydantic: image_policy.py (image references) and
schema_rules.py (schema contents). This file only wires them in.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .image_policy import ImagePolicyError, parse_image_ref
from .schema_rules import check_envelope

NAME_PATTERN = r"^[a-z][a-z0-9_]*$"  # matches the naming rule connector_sdk already enforces


class JsonSchemaEnvelope(BaseModel):
    """The exact shape describe_config()/describe_credentials() return.

    extra="forbid" matters here more than in most models: without it, a flat
    map like {"base_url": {"type": "string"}} isn't rejected -- none of its keys
    match type/properties/required, so pydantic would drop them as unrecognized
    and fall back to the defaults, producing a *silently empty* envelope that
    still validates.
    """

    model_config = ConfigDict(extra="forbid")

    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def contents_are_sensible(self) -> "JsonSchemaEnvelope":
        problems = check_envelope({"type": self.type, "properties": self.properties, "required": self.required})
        if problems:
            raise ValueError("; ".join(problems))
        return self


class ConnectorRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    image: str
    config_schema: JsonSchemaEnvelope
    credential_schema: JsonSchemaEnvelope

    @field_validator("name")
    @classmethod
    def name_matches_contract_rule(cls, v: str) -> str:
        if not re.fullmatch(NAME_PATTERN, v):
            raise ValueError(
                f"name must match {NAME_PATTERN!r} (lowercase letters, digits, "
                f"underscores, starting with a letter) -- got {v!r}"
            )
        return v

    @field_validator("image")
    @classmethod
    def image_reference_is_well_formed(cls, v: str) -> str:
        # Syntax only. Which registries are allowed, and whether the image is
        # pinned, is decided by the ImageValidator in the route (it needs config).
        try:
            parse_image_ref(v)
        except ImagePolicyError as exc:
            raise ValueError(f"{exc.code}: {exc.message}") from exc
        return v

    @field_validator("config_schema")
    @classmethod
    def config_has_no_secrets(cls, v: JsonSchemaEnvelope) -> JsonSchemaEnvelope:
        # A secret described under config would be stored and shown as plain
        # configuration. Non-secret credentials (a username, an email) are fine
        # in credential_schema, so that side has no matching rule.
        for field_name, field_def in v.properties.items():
            if isinstance(field_def, dict) and field_def.get("secret") is True:
                raise ValueError(
                    f"config_schema.properties.{field_name} is marked secret; "
                    f"describe secrets in credential_schema instead"
                )
        return v


class ConnectorRecord(BaseModel):
    """What's actually stored, and what GET returns."""

    name: str
    image: str
    config_schema: JsonSchemaEnvelope
    credential_schema: JsonSchemaEnvelope
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    image_check_status: str = "unchecked"  # "ok" once the reference passed the policy check
    # "passed" | "failed" | "not_scanned". Anything other than "passed" means the
    # image has NOT been vetted and must not be treated as safe to run.
    scan_status: str = "not_scanned"
