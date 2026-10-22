"""
Deeper validation for config_schema / credential_schema (stdlib only).

The pydantic model only proves the *envelope* is present (type / properties /
required, nothing else). These rules check that what is inside it makes sense.
Each of these was accepted by the old validation:

  - {"type": "banana"}
  - "required" naming a property that does not exist
  - a property that is a string instead of an object
  - a property with no "type", or a misspelt one ("strng")
  - an unbounded number of properties / an enormous schema
"""
from __future__ import annotations

import json
import re

MAX_PROPERTIES = 50
MAX_SCHEMA_BYTES = 16_384
PROPERTY_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
JSON_TYPES = frozenset({"string", "number", "integer", "boolean", "array", "object", "null"})


def check_envelope(schema: dict) -> list[str]:
    """Return a list of human-readable problems (empty list means valid)."""
    problems: list[str] = []

    if schema.get("type") != "object":
        problems.append('"type" must be "object"')

    props, required = schema.get("properties", {}), schema.get("required", [])
    if not isinstance(props, dict):
        return problems + ['"properties" must be an object']
    if not isinstance(required, list):
        return problems + ['"required" must be a list']

    if len(props) > MAX_PROPERTIES:
        problems.append(f"too many properties ({len(props)}; the limit is {MAX_PROPERTIES})")

    for name, definition in props.items():
        if not isinstance(name, str) or not PROPERTY_NAME_RE.match(name):
            problems.append(f"property name {name!r} is invalid (letters, digits and underscores, starting with a letter or underscore, at most 64 characters)")
            continue
        if not isinstance(definition, dict):
            problems.append(f"property {name!r} must be an object, not {type(definition).__name__}")
            continue
        if definition.get("type") not in JSON_TYPES:
            problems.append(f'property {name!r} needs a "type" that is one of {sorted(JSON_TYPES)}')
        if "secret" in definition and not isinstance(definition["secret"], bool):
            problems.append(f'property {name!r}: "secret" must be true or false')

    for item in required:
        if not isinstance(item, str):
            problems.append(f"required entries must be strings, not {type(item).__name__}")
        elif item not in props:
            problems.append(f"required field {item!r} is not defined in properties")

    try:
        if len(json.dumps(schema)) > MAX_SCHEMA_BYTES:
            problems.append(f"schema is larger than {MAX_SCHEMA_BYTES} bytes")
    except (TypeError, ValueError):
        problems.append("schema is not valid JSON")

    return problems
