"""
Tests for registration/schema_rules.py: what counts as a sensible
config_schema / credential_schema. No FastAPI or pydantic needed.

    pytest tests/test_schema_rules.py -v
"""
from __future__ import annotations

import pytest

from registration.schema_rules import MAX_PROPERTIES, MAX_SCHEMA_BYTES, check_envelope


def schema(properties=None, required=None, type="object"):
    return {"type": type, "properties": properties or {}, "required": required or []}


def test_the_reference_connectors_schemas_are_valid():
    config = schema({"base_url": {"type": "string", "description": "Base URL"}}, ["base_url"])
    creds = schema({"api_key": {"type": "string", "secret": True}}, ["api_key"])
    assert check_envelope(config) == [] and check_envelope(creds) == []


def test_jira_style_credentials_with_a_non_secret_email_are_valid():
    """The repo's own Jira connector describes a plain `email` next to a secret
    `api_token`. The old rule ('every credential must be secret') rejected it."""
    creds = schema(
        {"email": {"type": "string"}, "api_token": {"type": "string", "secret": True}},
        ["email", "api_token"],
    )
    assert check_envelope(creds) == []


def test_empty_schema_is_valid():
    assert check_envelope(schema()) == []


@pytest.mark.parametrize(
    "bad,fragment",
    [
        (schema(type="banana"), '"type" must be "object"'),
        (schema({"a": {"type": "string"}}, ["ghost"]), "'ghost' is not defined"),
        (schema({"a": "string"}), "must be an object"),
        (schema({"a": {}}), 'needs a "type"'),
        (schema({"a": {"type": "strng"}}), 'needs a "type"'),
        (schema({"a": {"type": "string", "secret": "yes"}}), '"secret" must be true or false'),
        (schema({"bad name": {"type": "string"}}), "property name"),
        (schema({"x" * 65: {"type": "string"}}), "property name"),
        (schema({"a": {"type": "string"}}, [["a"]]), "required entries must be strings"),
        ({"type": "object", "properties": [], "required": []}, '"properties" must be an object'),
        ({"type": "object", "properties": {}, "required": "a"}, '"required" must be a list'),
    ],
)
def test_malformed_content_is_reported(bad, fragment):
    problems = check_envelope(bad)
    assert problems, f"expected a problem for {bad!r}"
    assert any(fragment in p for p in problems), problems


def test_too_many_properties_are_rejected():
    many = {f"p{i}": {"type": "string"} for i in range(MAX_PROPERTIES + 1)}
    assert any("too many properties" in p for p in check_envelope(schema(many)))
    assert check_envelope(schema({f"p{i}": {"type": "string"} for i in range(MAX_PROPERTIES)})) == []


def test_oversized_schema_is_rejected():
    huge = schema({"a": {"type": "string", "description": "x" * (MAX_SCHEMA_BYTES + 1)}})
    assert any("larger than" in p for p in check_envelope(huge))


def test_every_problem_is_reported_not_just_the_first():
    problems = check_envelope(schema({"a": {}, "b": "x"}, ["ghost"], type="banana"))
    assert len(problems) >= 4
