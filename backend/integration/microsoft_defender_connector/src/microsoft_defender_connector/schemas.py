"""JSON Schemas returned by Connector.config_schema() and
Connector.credential_schema() — used by the Integration Hub UI
(FR-UI) to render the "connect Microsoft Defender" form and by
POST /integrations to validate submitted config."""

CONFIG_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Microsoft Defender Connector Config",
    "type": "object",
    "required": ["tenant_id", "client_id"],
    "properties": {
        "tenant_id": {"type": "string", "description": "Azure AD tenant ID"},
        "client_id": {"type": "string", "description": "App registration (client) ID"},
        "api_base_url": {
            "type": "string",
            "format": "uri",
            "default": "https://api.securitycenter.microsoft.com",
        },
        "login_base_url": {
            "type": "string",
            "format": "uri",
            "default": "https://login.microsoftonline.com",
        },
        "poll_interval_minutes": {"type": "integer", "minimum": 5, "default": 15},
        "machine_page_size": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 500},
        "alert_lookback_hours": {"type": "integer", "minimum": 1, "default": 24},
        "request_timeout_seconds": {"type": "number", "exclusiveMinimum": 0, "default": 30.0},
    },
    "additionalProperties": False,
}

# Credentials are never persisted alongside config — this schema describes
# what must exist at the Vault path referenced by integrations.credentials_ref.
CREDENTIAL_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Microsoft Defender Connector Credentials (Vault)",
    "type": "object",
    "required": ["client_secret"],
    "properties": {
        "client_secret": {
            "type": "string",
            "description": "Azure AD app registration client secret",
        }
    },
    "additionalProperties": False,
}
