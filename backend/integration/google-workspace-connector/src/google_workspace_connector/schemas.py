CONFIG_SCHEMA = {
    "type": "object",
    "required": ["customer_id", "domain", "admin_user"],
    "properties": {
        "customer_id": {"type": "string", "minLength": 1},
        "domain": {"type": "string", "minLength": 1},
        "admin_user": {"type": "string", "format": "email"},
        "sync": {
            "type": "object",
            "properties": {
                "users": {"type": "boolean", "default": True},
                "audit_logs": {"type": "boolean", "default": True},
                "audit_application": {"type": "string", "default": "login"},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 500},
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}

CREDENTIAL_SCHEMA = {
    "type": "object",
    "required": ["service_account"],
    "properties": {
        "service_account": {
            "type": "object",
            "description": "Reference/metadata consumed by the Google Workspace auth module.",
            "required": ["client_email"],
            "properties": {
                "client_email": {"type": "string", "format": "email"},
                "private_key_ref": {
                    "type": "string",
                    "description": "Vault reference; never the private key itself.",
                },
            },
            "additionalProperties": False,
        }
    },
    "additionalProperties": False,
}
