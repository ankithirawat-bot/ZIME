"""
Tests for configuration validation and secret management.
"""

from __future__ import annotations

from backend.core.config_validation import (
    ConfigField,
    is_non_empty,
    is_port,
    is_url,
    mask_secret,
    mask_url,
    safe_format,
    validate_config,
)

# ---------------------------------------------------------------------------
# Secret masking
# ---------------------------------------------------------------------------


class TestMaskSecret:
    def test_empty_string(self) -> None:
        assert mask_secret("") == ""

    def test_short_value(self) -> None:
        assert mask_secret("ab") == "****"
        assert mask_secret("abc") == "****"
        assert mask_secret("abcdef") == "****"

    def test_long_value(self) -> None:
        result = mask_secret("my-api-key-123")
        assert result == "my****23"
        assert "api" not in result

    def test_api_key(self) -> None:
        result = mask_secret("sk_live_abc123def456")
        assert result == "sk****56"
        assert "abc123def" not in result


class TestMaskUrl:
    def test_no_credentials(self) -> None:
        assert mask_url("http://example.com") == "http://example.com"

    def test_with_password(self) -> None:
        result = mask_url("postgresql+psycopg://user:secret@localhost:5432/db")
        assert result == "postgresql+psycopg://user:****@localhost:5432/db"
        assert "secret" not in result

    def test_no_password(self) -> None:
        result = mask_url("postgresql+psycopg://user@localhost/db")
        assert result == "postgresql+psycopg://user@localhost/db"


class TestSafeFormat:
    def test_non_secret(self) -> None:
        field = ConfigField(name="EXCHANGE", secret=False)
        assert safe_format("NSE", field) == "NSE"

    def test_secret_masked(self) -> None:
        field = ConfigField(name="API_KEY", secret=True)
        result = safe_format("sk_live_key_value", field)
        assert result == "sk****ue"
        assert "key_value" not in result

    def test_empty(self) -> None:
        field = ConfigField(name="EMPTY", secret=True)
        assert safe_format("", field) == ""


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


class TestValidators:
    def test_is_non_empty(self) -> None:
        assert is_non_empty("hello") is True
        assert is_non_empty(" ") is False
        assert is_non_empty("") is False

    def test_is_port(self) -> None:
        assert is_port("5432") is True
        assert is_port("1") is True
        assert is_port("65535") is True
        assert is_port("0") is False
        assert is_port("70000") is False
        assert is_port("not_a_port") is False
        assert is_port("") is False

    def test_is_url(self) -> None:
        assert is_url("postgresql://host/db") is True
        assert is_url("http://example.com") is True
        assert is_url("") is False
        assert is_url("localhost") is False


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


class TestValidateConfig:
    def test_all_optional_missing(self) -> None:
        """Missing optional fields should not fail."""
        fields = (
            ConfigField(name="OPTIONAL_KEY", required=False, secret=True),
        )
        report = validate_config(fields, source={})
        assert report.all_valid is True
        assert report.passed == 1

    def test_required_missing(self) -> None:
        """Missing required fields should fail."""
        fields = (
            ConfigField(name="REQUIRED_KEY", required=True, description="Test"),
        )
        report = validate_config(fields, source={})
        assert report.all_valid is False
        assert report.failed == 1
        assert "missing" in report.results[0].errors[0].lower()

    def test_required_with_value(self) -> None:
        """Required fields with values should pass."""
        fields = (
            ConfigField(name="REQUIRED_KEY", required=True),
        )
        report = validate_config(fields, source={"REQUIRED_KEY": "abc"})
        assert report.all_valid is True

    def test_validator_fails(self) -> None:
        """Fields with failing validators should fail."""
        fields = (
            ConfigField(name="PORT", validator=is_port),
        )
        report = validate_config(fields, source={"PORT": "99999"})
        assert report.all_valid is False
        assert report.failed == 1

    def test_validator_passes(self) -> None:
        """Fields with passing validators should succeed."""
        fields = (
            ConfigField(name="PORT", validator=is_port),
        )
        report = validate_config(fields, source={"PORT": "8080"})
        assert report.all_valid is True

    def test_insecure_default_rejected(self) -> None:
        """Using the default value for a secret should fail."""
        fields = (
            ConfigField(
                name="DB_PASSWORD",
                required=True,
                secret=True,
                default="changeme",
                description="Database password",
            ),
        )
        report = validate_config(fields, source={})
        assert report.all_valid is False
        assert "default" in report.results[0].errors[0].lower()

    def test_secret_value_masked_in_result(self) -> None:
        """Validation result values should be masked for secrets."""
        fields = (
            ConfigField(name="API_KEY", secret=True),
        )
        report = validate_config(fields, source={"API_KEY": "my-secret-key-123"})
        assert report.results[0].value != "my-secret-key-123"
        assert "secret" not in report.results[0].value
        assert "****" in report.results[0].value

    def test_non_secret_value_visible(self) -> None:
        """Non-secret values should be visible in results."""
        fields = (
            ConfigField(name="EXCHANGE", secret=False),
        )
        report = validate_config(fields, source={"EXCHANGE": "NSE"})
        assert report.results[0].value == "NSE"

    def test_default_used_when_source_missing(self) -> None:
        """Default should be used when source doesn't have the key."""
        fields = (
            ConfigField(name="TIMEOUT", default="30", validator=is_non_empty),
        )
        report = validate_config(fields, source={})
        assert report.all_valid is True
        assert report.results[0].value == "30"

    def test_source_overrides_default(self) -> None:
        """Source value should override default."""
        fields = (
            ConfigField(name="TIMEOUT", default="30"),
        )
        report = validate_config(fields, source={"TIMEOUT": "60"})
        assert report.results[0].value == "60"

    def test_multiple_errors(self) -> None:
        """Multiple config errors should all be reported."""
        fields = (
            ConfigField(name="REQUIRED_ONE", required=True),
            ConfigField(name="REQUIRED_TWO", required=True, validator=is_port),
        )
        report = validate_config(fields, source={"REQUIRED_TWO": "invalid"})
        assert report.failed == 2
        assert report.total == 2

    def test_report_counts(self) -> None:
        """Report counts should reflect actual results."""
        fields = (
            ConfigField(name="A", required=True),
            ConfigField(name="B", required=True, validator=is_port),
            ConfigField(name="C"),
        )
        source = {"A": "value", "B": "5432"}
        report = validate_config(fields, source)
        assert report.total == 3
        assert report.passed == 3
        assert report.failed == 0
        assert report.all_valid is True


# ---------------------------------------------------------------------------
# Startup integration (smoke-level)
# ---------------------------------------------------------------------------


class TestStartupIntegration:
    """Verify config validation can be run from startup context."""

    def test_startup_config_check_exists(self) -> None:
        from backend.core.startup_validation import (
            _DEFAULT_CHECKS,
        )

        check_names = {c.__name__ for c in _DEFAULT_CHECKS}
        assert "_check_config_values" in check_names
