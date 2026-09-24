import json
import os
import jsonschema
from jsonschema import FormatChecker
from typing import Dict, Any, Tuple, List, Optional
from src.interfaces.base_validator import BaseValidator


class AssetValidator(BaseValidator):
    """Validates normalized CAM payloads against azure_cam_schema.json."""

    def __init__(self, schema_path: Optional[str] = None) -> None:
        if not schema_path:
            # Default relative path from src/validator.py to contracts/azure_cam_schema.json
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            schema_path = os.path.join(base_dir, "contracts", "azure_cam_schema.json")

        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"Schema contract not found at: {schema_path}")

        with open(schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)

        self.validator = jsonschema.Draft7Validator(
            self.schema, 
            format_checker=FormatChecker()
        )

    def validate(self, asset_payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates an asset dictionary against the JSON Schema contract.
        
        :param asset_payload: Normalized asset dictionary.
        :return: Tuple of (is_valid: bool, list_of_error_strings: List[str]).
        """
        errors: List[str] = []
        for error in self.validator.iter_errors(asset_payload):
            path = " -> ".join(str(p) for p in error.path) if error.path else "root"
            errors.append(f"[{path}]: {error.message}")

        return len(errors) == 0, errors
