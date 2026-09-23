"""Tests for config / credential schema handling (Sections 18-19)."""

import pytest

from connector_sdk import (
    ConfigurationError,
    ContractViolation,
    CredentialError,
    assert_valid_schema,
    field,
    object_schema,
    redact,
    secret_field,
    validate_against_schema,
)


class TestSchemaShape:
    def test_valid_config_schema(self):
        assert_valid_schema(
            object_schema({"region": field("string")}, required=["region"]), kind="config"
        )

    def test_valid_credential_schema(self):
        assert_valid_schema(
            object_schema({"api_key": secret_field()}, required=["api_key"]), kind="credentials"
        )

    def test_non_dict_rejected(self):
        with pytest.raises(ContractViolation):
            assert_valid_schema(["region"], kind="config")

    def test_required_field_must_exist_in_properties(self):
        with pytest.raises(ContractViolation, match="not in 'properties'"):
            assert_valid_schema(
                {"type": "object", "properties": {}, "required": ["ghost"]}, kind="config"
            )

    def test_secret_in_config_is_rejected(self):
        schema = object_schema({"client_secret": field("string")})
        with pytest.raises(ContractViolation, match="must not declare secret"):
            assert_valid_schema(schema, kind="config")

    def test_unmarked_credential_is_rejected(self):
        schema = object_schema({"api_key": field("string")})
        with pytest.raises(ContractViolation, match="secret"):
            assert_valid_schema(schema, kind="credentials")

    def test_unsupported_type_rejected(self):
        with pytest.raises(ContractViolation):
            field("datetime")


class TestValueValidation:
    schema = object_schema(
        {"region": field("string"), "page_size": field("integer")}, required=["region"]
    )

    def test_accepts_valid_values(self):
        validate_against_schema({"region": "eastus", "page_size": 10}, self.schema)

    def test_missing_required_field(self):
        with pytest.raises(ConfigurationError, match="region"):
            validate_against_schema({}, self.schema)

    def test_wrong_type(self):
        with pytest.raises(ConfigurationError, match="page_size"):
            validate_against_schema({"region": "eastus", "page_size": "ten"}, self.schema)

    def test_bool_is_not_an_integer(self):
        with pytest.raises(ConfigurationError):
            validate_against_schema({"region": "eastus", "page_size": True}, self.schema)

    def test_credential_errors_use_credential_class(self):
        creds = object_schema({"api_key": secret_field()}, required=["api_key"])
        with pytest.raises(CredentialError):
            validate_against_schema({}, creds, kind="credentials")

    def test_error_message_never_contains_the_value(self):
        creds = object_schema({"api_key": secret_field()}, required=["api_key"])
        with pytest.raises(CredentialError) as exc:
            validate_against_schema({"api_key": 12345}, creds, kind="credentials")
        assert "12345" not in str(exc.value)


class TestRedaction:
    def test_declared_secrets_are_redacted(self):
        schema = object_schema({"api_key": secret_field()}, required=["api_key"])
        assert redact({"api_key": "super-secret"}, schema)["api_key"] == "***REDACTED***"

    def test_secret_looking_names_are_redacted_even_if_undeclared(self):
        assert redact({"client_secret": "x"}, {"properties": {}})["client_secret"] == "***REDACTED***"

    def test_non_secrets_pass_through(self):
        assert redact({"region": "eastus"}, {"properties": {}})["region"] == "eastus"
