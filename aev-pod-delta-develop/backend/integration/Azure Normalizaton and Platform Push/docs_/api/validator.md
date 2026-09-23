#Validation Engine & Schema Docs

# Validation Engine Documentation

The validation module (`src/validator.py`) enforces strict compliance against `contracts/azure_cam_schema.json`.

```python
from src.validator import PayloadValidator

validator = PayloadValidator()
is_valid, errors = validator.validate(normalized_payload)

if not is_valid:
    print(f"Schema Validation Errors: {errors}")
