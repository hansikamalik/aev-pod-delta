"""Configuration and Credential schemas for Splunk Integration."""

def get_config_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "host": {
                "type": "string",
                "description": "Splunk Search Head or Management IP/FQDN"
            },
            "port": {
                "type": "integer",
                "default": 8089,
                "description": "Splunk REST API management port"
            },
            "verify_ssl": {
                "type": "boolean",
                "default": True,
                "description": "Enforce SSL certificate verification"
            },
            "batch_size": {
                "type": "integer",
                "default": 100,
                "description": "Max events per pull iteration"
            },
            "search_query": {
                "type": "string",
                "default": "search index=_internal sourcetype=splunkd_ui_access",
                "description": "Splunk SPL search query"
            }
        },
        "required": ["host"]
    }


def get_credentials_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "bearer_token": {
                "type": "string",
                "secret": True,
                "description": "Vault Key Path: secret/data/connectors/splunk#bearer_token"
            }
        },
        "required": ["bearer_token"]
    }
