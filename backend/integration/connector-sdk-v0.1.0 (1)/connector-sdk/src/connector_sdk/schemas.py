"""Helpers for building and validating config / credential schemas.

Contract references:
  - Section 18 (Configuration Contract)
  - Section 19 (Credential Contract)

Both ``describe_config()`` and ``describe_credentials()`` return a plain
JSON-Schema-shaped ``dict``. These helpers exist so every connector emits
the same shape, and so the SDK can enforce the two hard rules:

  * configuration MUST NOT contain credentials or secrets
  * credential fields MUST be marked ``"secret": True``

A tiny validator is included rather than a ``jsonschema`` dependency; the
SDK stays stdlib-only. Swap in full JSON Schema validation later behind
:func:`validate_against_schema` without changing any connector.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .exceptions import ConfigurationError, ContractViolation, CredentialError

_JSON_TYPES: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": (list, tuple),
}

# Field names that must never appear in a non-secret configuration schema.
_SECRET_HINTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private_key",
    "credential",
    "client_secret",
    "passphrase",
)


def object_schema(
    properties: Mapping[str, Mapping[str, Any]],
    required: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Build an ``{"type": "object", ...}`` schema.

    Example::

        return object_schema(
            {"region": {"type": "string"}},
            required=["region"],
        )
    """
    return {
        "type": "object",
        "properties": {key: dict(value) for key, value in properties.items()},
        "required": list(required or []),
    }


def field(
    type_: str = "string",
    *,
    description: str | None = None,
    secret: bool = False,
    default: Any = None,
    enum: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Build a single property entry for :func:`object_schema`."""
    if type_ not in _JSON_TYPES:
        raise ContractViolation(
            f"Unsupported schema type {type_!r}. Supported: {', '.join(sorted(_JSON_TYPES))}"
        )
    spec: dict[str, Any] = {"type": type_}
    if description:
        spec["description"] = description
    if secret:
        spec["secret"] = True
    if default is not None:
        spec["default"] = default
    if enum is not None:
        spec["enum"] = list(enum)
    return spec


def secret_field(description: str | None = None) -> dict[str, Any]:
    """Shorthand for a required secret string, for ``describe_credentials()``."""
    return field("string", description=description, secret=True)


def assert_valid_schema(schema: Any, *, kind: str = "config") -> None:
    """Validate the *shape* of a schema returned by a connector.

    Raises :class:`ContractViolation` when the schema is malformed, or when
    a config schema declares a field that looks like a secret.
    """
    if not isinstance(schema, dict):
        raise ContractViolation(f"describe_{kind}() must return a dict, got {type(schema).__name__}")
    if schema.get("type") != "object":
        raise ContractViolation(f"describe_{kind}() must return a schema of type 'object'")

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise ContractViolation(f"describe_{kind}() 'properties' must be a dict")

    required = schema.get("required", [])
    if not isinstance(required, (list, tuple)):
        raise ContractViolation(f"describe_{kind}() 'required' must be a list")

    for name in required:
        if name not in properties:
            raise ContractViolation(
                f"describe_{kind}() declares required field {name!r} that is not in 'properties'"
            )

    for name, spec in properties.items():
        if not isinstance(spec, dict) or "type" not in spec:
            raise ContractViolation(
                f"describe_{kind}() property {name!r} must be a dict containing a 'type'"
            )
        if spec["type"] not in _JSON_TYPES:
            raise ContractViolation(
                f"describe_{kind}() property {name!r} has unsupported type {spec['type']!r}"
            )

        is_secret = bool(spec.get("secret"))
        looks_secret = any(hint in name.lower() for hint in _SECRET_HINTS)

        if kind == "config" and (is_secret or looks_secret):
            raise ContractViolation(
                f"describe_config() must not declare secret field {name!r}. "
                "Move it to describe_credentials()."
            )
        if kind == "credentials" and not is_secret:
            raise ContractViolation(
                f"describe_credentials() property {name!r} must be marked \"secret\": True"
            )


def validate_against_schema(
    values: Mapping[str, Any],
    schema: Mapping[str, Any],
    *,
    kind: str = "config",
) -> None:
    """Check ``values`` against ``schema``: required keys present, types match.

    Raises :class:`ConfigurationError` or :class:`CredentialError` depending
    on ``kind``. Error messages never include the offending value, so this is
    safe to call on credentials.
    """
    error_cls = CredentialError if kind == "credentials" else ConfigurationError

    properties: Mapping[str, Any] = schema.get("properties", {})
    missing = [name for name in schema.get("required", []) if values.get(name) in (None, "")]
    if missing:
        raise error_cls(
            f"Missing required {kind} field(s): {', '.join(sorted(missing))}",
            operation=f"validate_{kind}",
        )

    for name, value in values.items():
        spec = properties.get(name)
        if spec is None or value is None:
            continue
        expected = _JSON_TYPES.get(spec.get("type", "string"), str)
        # bool is a subclass of int; keep them distinct.
        if spec.get("type") in {"integer", "number"} and isinstance(value, bool):
            raise error_cls(
                f"{kind.capitalize()} field {name!r} must be of type {spec['type']}",
                operation=f"validate_{kind}",
            )
        if not isinstance(value, expected):
            raise error_cls(
                f"{kind.capitalize()} field {name!r} must be of type {spec['type']}",
                operation=f"validate_{kind}",
            )
        if "enum" in spec and value not in spec["enum"]:
            raise error_cls(
                f"{kind.capitalize()} field {name!r} is not one of the allowed values",
                operation=f"validate_{kind}",
            )


def redact(values: Mapping[str, Any], schema: Mapping[str, Any]) -> dict[str, Any]:
    """Return ``values`` with every schema-declared secret replaced.

    Use this before logging anything derived from credentials.
    """
    properties: Mapping[str, Any] = schema.get("properties", {})
    out: dict[str, Any] = {}
    for name, value in values.items():
        spec = properties.get(name, {})
        if spec.get("secret") or any(hint in name.lower() for hint in _SECRET_HINTS):
            out[name] = "***REDACTED***"
        else:
            out[name] = value
    return out


__all__ = [
    "object_schema",
    "field",
    "secret_field",
    "assert_valid_schema",
    "validate_against_schema",
    "redact",
]
