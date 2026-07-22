"""
Configuration validation and secret management.

Centralizes configuration metadata, validates required values, and
provides secret masking for safe logging.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Secret masking
# ---------------------------------------------------------------------------

_MASK = "****"

_CREDENTIAL_PATTERN = re.compile(
    r"(://)([^:]+):([^@]+)@",
)


def mask_url(url: str) -> str:
    """Mask credentials embedded in a URL.

    ``postgresql+psycopg://user:password@host/db``
    ``→`` ``postgresql+psycopg://user:****@host/db``

    Args:
        url: A URL that may contain ``user:password``.

    Returns:
        URL with the password portion replaced by ``****``.
    """
    return _CREDENTIAL_PATTERN.sub(r"\1\2:****@", url)


def mask_secret(value: str) -> str:
    """Mask a secret value for safe logging.

    Examples::

        >>> mask_secret("my-api-key-123")
        'my****123'
        >>> mask_secret("ab")
        '****'
        >>> mask_secret("")
        ''

    Args:
        value: The secret string to mask.

    Returns:
        Masked string with middle characters replaced by ``****``.
    """
    if not value:
        return ""
    if len(value) <= 6:
        return _MASK
    return value[:2] + _MASK + value[-2:]


# ---------------------------------------------------------------------------
# Config field metadata
# ---------------------------------------------------------------------------

Validator = Callable[[str], bool]


@dataclass(frozen=True)
class ConfigField:
    """Metadata for a single configuration value.

    Attributes:
        name:        Configuration key name.
        required:    Whether the value must be non-empty.
        secret:      Whether the value is a secret (API key, password, token).
        default:     Fallback value when the source is empty.
        validator:   Optional callable that returns ``True`` for valid input.
        description: Human-readable description of this config value.
    """

    name: str
    required: bool = False
    secret: bool = False
    default: str | None = None
    validator: Validator | None = None
    description: str = ""


# ---------------------------------------------------------------------------
# Common validators
# ---------------------------------------------------------------------------


def is_non_empty(value: str) -> bool:
    """Return ``True`` if *value* is non-empty after stripping."""
    return bool(value.strip())


def is_port(value: str) -> bool:
    """Return ``True`` if *value* is a valid TCP port number."""
    try:
        port = int(value)
        return 1 <= port <= 65535
    except (ValueError, TypeError):
        return False


def is_url(value: str) -> bool:
    """Return ``True`` if *value* looks like a URL with a scheme."""
    return bool(re.match(r"^\w+://", value.strip()))


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------


@dataclass
class ConfigValidationResult:
    """Result of validating configuration values.

    Attributes:
        field:      The config field metadata.
        value:      Raw value provided.
        passed:     Whether the value passed all checks.
        errors:     Human-readable error messages.
    """

    field: ConfigField
    value: str
    passed: bool = True
    errors: list[str] = field(default_factory=list)


@dataclass
class ConfigValidationReport:
    """Aggregated configuration validation report.

    Attributes:
        results:     Per-field validation results.
        all_valid:   ``True`` if every field passed.
        total:       Number of fields checked.
        passed:      Number of fields that passed.
        failed:      Number of fields that failed.
    """

    results: list[ConfigValidationResult] = field(default_factory=list)
    all_valid: bool = True
    total: int = 0
    passed: int = 0
    failed: int = 0


def validate_config(
    fields: tuple[ConfigField, ...],
    source: dict[str, str] | None = None,
) -> ConfigValidationReport:
    """Validate configuration values against field metadata.

    Args:
        fields:  Metadata describing each configuration value.
        source:  Dict of name → value (e.g. from ``os.environ``).
                 Uses field defaults for missing keys.

    Returns:
        ConfigValidationReport with per-field results.
    """
    source = source or {}
    results: list[ConfigValidationResult] = []

    for field_meta in fields:
        raw = source.get(field_meta.name)
        if raw is None or (not raw and field_meta.default is not None):
            raw = field_meta.default if field_meta.default is not None else ""
        if raw is None:
            raw = ""

        errors: list[str] = []

        if field_meta.required and not raw.strip():
            errors.append(f"Required field '{field_meta.name}' is missing or empty")

        if raw.strip() and field_meta.validator is not None:
            if not field_meta.validator(raw):
                errors.append(
                    f"Field '{field_meta.name}' failed validation"
                )

        # Reject insecure defaults for secrets
        if field_meta.secret and field_meta.default is not None:
            if raw == field_meta.default:
                errors.append(
                    f"Secret '{field_meta.name}' is using its default value — "
                    "set a real value in the environment"
                )

        results.append(
            ConfigValidationResult(
                field=field_meta,
                value=mask_secret(raw) if field_meta.secret else raw,
                passed=len(errors) == 0,
                errors=errors,
            )
        )

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    return ConfigValidationReport(
        results=results,
        all_valid=failed == 0,
        total=len(results),
        passed=passed,
        failed=failed,
    )


def safe_format(value: str, field: ConfigField) -> str:
    """Return a log-safe representation of a configuration value.

    Secrets are masked; non-secrets are returned as-is.

    Args:
        value: The raw configuration value.
        field: The field metadata (determines masking).

    Returns:
        ``"****"`` if the field is a secret, otherwise *value*.
    """
    if not value:
        return ""
    if field.secret:
        return mask_secret(value)
    return value


# ---------------------------------------------------------------------------
# Pre-defined configuration fields
# ---------------------------------------------------------------------------

_DATABASE_URL_FIELD = ConfigField(
    name="DATABASE_URL",
    required=True,
    secret=True,
    description="SQLAlchemy database connection URL",
    validator=is_url,
)

_UPSTOX_API_KEY = ConfigField(
    name="UPSTOX_API_KEY",
    required=False,
    secret=True,
    description="Upstox API key for market data",
)

_UPSTOX_API_SECRET = ConfigField(
    name="UPSTOX_API_SECRET",
    required=False,
    secret=True,
    description="Upstox API secret",
)

_UPSTOX_ACCESS_TOKEN = ConfigField(
    name="UPSTOX_ACCESS_TOKEN",
    required=False,
    secret=True,
    description="Upstox OAuth access token",
)

DEFAULT_CONFIG_FIELDS: tuple[ConfigField, ...] = (
    _DATABASE_URL_FIELD,
    _UPSTOX_API_KEY,
    _UPSTOX_API_SECRET,
    _UPSTOX_ACCESS_TOKEN,
)
