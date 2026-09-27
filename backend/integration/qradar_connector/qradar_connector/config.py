from typing import Any, Dict

def get_config_schema() -> Dict[str, Any]:
    """Describes non-secret configuration parameters."""
    return {
        "type": "object",
        "properties": {
            "host": {
                "type": "string",
                "description": "FQDN or IP address of the QRadar Console (e.g., qradar.example.com)"
            },
            "verify_ssl": {
                "type": "boolean",
                "default": True,
                "description": "Whether to verify SSL certificates on REST API requests"
            },
            "api_version": {
                "type": "string",
                "default": "19.0",
                "description": "QRadar REST API version header (e.g., 19.0)"
            }
        },
        "required": ["host"]
    }


def get_credentials_schema() -> Dict[str, Any]:
    """Describes secret credential requirements."""
    return {
        "type": "object",
        "properties": {
            "sec_token": {
                "type": "string",
                "secret": True,
                "description": "QRadar Authorized Service Security Token (SEC header)"
            }
        },
        "required": ["sec_token"]
    }
