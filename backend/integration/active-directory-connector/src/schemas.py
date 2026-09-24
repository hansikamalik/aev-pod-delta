"""JSON Schemas returned by Connector.config_schema() and
Connector.credential_schema() — used by the Integration Hub UI
(FR-UI) to render the "connect Active Directory" form and by
POST /integrations to validate submitted config."""

CONFIG_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Active Directory Connector Config",
    "type": "object",
    "required": ["ldap_server", "bind_dn", "base_dn"],
    "properties": {
        "ldap_server": {"type": "string", "description": "Domain controller hostname or IP"},
        "ldap_port": {"type": "integer", "default": 636},
        "use_ssl": {"type": "boolean", "default": True, "description": "Use LDAPS"},
        "bind_dn": {"type": "string", "description": "Service account DN for the LDAP simple bind"},
        "base_dn": {"type": "string", "description": "Root DN of the domain"},
        "user_search_base": {"type": ["string", "null"], "default": None},
        "user_search_filter": {
            "type": "string",
            "default": "(&(objectClass=user)(objectCategory=person))",
        },
        "group_search_base": {"type": ["string", "null"], "default": None},
        "group_search_filter": {"type": "string", "default": "(objectClass=group)"},
        "sync_groups": {"type": "boolean", "default": True},
        "page_size": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 500},
        "connect_timeout_seconds": {"type": "number", "exclusiveMinimum": 0, "default": 10.0},
        "receive_timeout_seconds": {"type": "number", "exclusiveMinimum": 0, "default": 30.0},
    },
    "additionalProperties": False,
}

# Credentials are never persisted alongside config — this schema describes
# what must exist at the Vault path referenced by integrations.credentials_ref.
CREDENTIAL_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Active Directory Connector Credentials (Vault)",
    "type": "object",
    "required": ["bind_password"],
    "properties": {
        "bind_password": {
            "type": "string",
            "description": "Password for the service account identified by config.bind_dn",
        }
    },
    "additionalProperties": False,
}
