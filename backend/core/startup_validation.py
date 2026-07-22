"""
Startup dependency validation.

Validates all critical dependencies during application startup and
fails fast with clear diagnostics if any required dependency is
unavailable or misconfigured.
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

logger = logging.getLogger("zime.startup")


class ValidationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class ValidationResult:
    """Result of a single validation check.

    Attributes:
        component:  Name of the component being validated.
        status:     PASS or FAIL.
        message:    Human-readable description of the result.
        remediation: Optional hint for resolving the issue.
    """

    component: str
    status: ValidationStatus
    message: str
    remediation: str | None = None


@dataclass(frozen=True)
class StartupValidationReport:
    """Aggregated startup validation report.

    Attributes:
        results:       All validation results.
        all_passed:    True if every check passed.
        run_at:        UTC timestamp of the validation run.
        total:         Total number of checks.
        passed:        Number of checks that passed.
        failed:        Number of checks that failed.
    """

    results: tuple[ValidationResult, ...] = ()
    all_passed: bool = True
    run_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    total: int = 0
    passed: int = 0
    failed: int = 0


# Each check is a callable that returns a ValidationResult.
ValidationCheck = Callable[[], ValidationResult]


def _check_database_connectivity() -> ValidationResult:
    """Verify that the database engine can connect."""
    try:
        from backend.app.database.database import engine

        with engine.connect() as conn:
            conn.execute(
                __import__("sqlalchemy").text("SELECT 1"),
            )
        return ValidationResult(
            component="database",
            status=ValidationStatus.PASS,
            message="Database connection verified",
        )
    except Exception as exc:
        return ValidationResult(
            component="database",
            status=ValidationStatus.FAIL,
            message=f"Database connection failed: {exc}",
            remediation="Check DATABASE_URL and ensure PostgreSQL is running",
        )


def _check_config_validity() -> ValidationResult:
    """Validate that critical configuration constants are sensible."""
    from backend.core.constants import (
        DB_PORT_DEFAULT,
        DEFAULT_EXCHANGE,
        DEFAULT_MAX_POSITION_SIZE,
        DEFAULT_MIN_POSITION_SIZE,
    )

    issues: list[str] = []

    if not DEFAULT_EXCHANGE:
        issues.append("DEFAULT_EXCHANGE is empty")
    if DEFAULT_MIN_POSITION_SIZE < 0:
        issues.append("DEFAULT_MIN_POSITION_SIZE is negative")
    if DEFAULT_MAX_POSITION_SIZE <= 0:
        issues.append("DEFAULT_MAX_POSITION_SIZE must be positive")
    if DEFAULT_MAX_POSITION_SIZE < DEFAULT_MIN_POSITION_SIZE:
        issues.append("DEFAULT_MAX_POSITION_SIZE < DEFAULT_MIN_POSITION_SIZE")
    if DB_PORT_DEFAULT <= 0 or DB_PORT_DEFAULT > 65535:
        issues.append("DB_PORT_DEFAULT out of range")

    if issues:
        return ValidationResult(
            component="configuration",
            status=ValidationStatus.FAIL,
            message="; ".join(issues),
            remediation="Review backend/core/constants.py",
        )
    return ValidationResult(
        component="configuration",
        status=ValidationStatus.PASS,
        message="Configuration constants are valid",
    )


def _check_environment_variables(
    required_vars: tuple[str, ...] | None = None,
) -> ValidationResult:
    """Check that required environment variables are set.

    Args:
        required_vars: Names of expected environment variables.
                       Defaults to an empty tuple (no required vars).
    """
    missing: list[str] = []
    for var in required_vars or ():
        if not os.getenv(var):
            missing.append(var)

    if missing:
        return ValidationResult(
            component="environment",
            status=ValidationStatus.FAIL,
            message=f"Missing required environment variables: {', '.join(missing)}",
            remediation="Set the missing variables or add defaults to backend/core/constants.py",
        )
    return ValidationResult(
        component="environment",
        status=ValidationStatus.PASS,
        message="Required environment variables are set",
    )


def _check_temp_directory() -> ValidationResult:
    """Verify that the system temp directory is writable."""
    try:
        with tempfile.NamedTemporaryFile(delete=True) as f:
            f.write(b"startup_validation")
        return ValidationResult(
            component="temp_directory",
            status=ValidationStatus.PASS,
            message="Temporary directory is writable",
        )
    except Exception as exc:
        return ValidationResult(
            component="temp_directory",
            status=ValidationStatus.FAIL,
            message=f"Temp directory not writable: {exc}",
            remediation="Check system TEMP / TMP environment variables",
        )


def _check_app_metadata() -> ValidationResult:
    """Verify that application metadata loads correctly."""
    try:
        from backend.core.app_metadata import get_app_metadata

        meta = get_app_metadata()
        if not meta.version or meta.version == "0.0.0":
            return ValidationResult(
                component="app_metadata",
                status=ValidationStatus.FAIL,
                message="Application version could not be read from pyproject.toml",
                remediation="Ensure pyproject.toml contains [project] version",
            )
        return ValidationResult(
            component="app_metadata",
            status=ValidationStatus.PASS,
            message=f"App metadata loaded (version={meta.version})",
        )
    except Exception as exc:
        return ValidationResult(
            component="app_metadata",
            status=ValidationStatus.FAIL,
            message=f"App metadata load failed: {exc}",
            remediation="Check backend/core/app_metadata.py",
        )


def _check_config_values() -> ValidationResult:
    """Validate configuration values using :mod:`config_validation`."""
    from backend.core.config_validation import (
        DEFAULT_CONFIG_FIELDS,
        validate_config,
    )

    try:
        import os

        source = {f.name: os.environ.get(f.name, "") for f in DEFAULT_CONFIG_FIELDS}
        report = validate_config(DEFAULT_CONFIG_FIELDS, source)

        if report.all_valid:
            return ValidationResult(
                component="config_values",
                status=ValidationStatus.PASS,
                message=f"All {report.total} configuration values valid",
            )

        details = "; ".join(
            "; ".join(r.errors) for r in report.results if not r.passed
        )
        return ValidationResult(
            component="config_values",
            status=ValidationStatus.FAIL,
            message=f"{report.failed} configuration error(s): {details}",
            remediation="Set the required environment variables or check backend/core/config_validation.py",
        )
    except Exception as exc:
        return ValidationResult(
            component="config_values",
            status=ValidationStatus.FAIL,
            message=f"Config validation failed: {exc}",
            remediation="Review backend/core/config_validation.py",
        )


# ---------------------------------------------------------------------------
# Default check registry
# ---------------------------------------------------------------------------

_DEFAULT_CHECKS: tuple[ValidationCheck, ...] = (
    _check_config_validity,
    _check_config_values,
    _check_database_connectivity,
    _check_temp_directory,
    _check_app_metadata,
)


def run_startup_validations(
    extra_checks: tuple[ValidationCheck, ...] | None = None,
    required_env_vars: tuple[str, ...] | None = None,
) -> StartupValidationReport:
    """Run all registered startup validations.

    This function is designed to be extensible — add new checks by
    passing them via *extra_checks* or by appending to
    ``_DEFAULT_CHECKS``.

    Args:
        extra_checks:    Additional checks beyond the defaults.
        required_env_vars: Environment variable names that must be set.

    Returns:
        StartupValidationReport with per-check results.
    """
    checks: list[ValidationCheck] = list(_DEFAULT_CHECKS)

    if required_env_vars:
        # Bind the tuple so the closure captures the current value
        vars_to_check = required_env_vars

        def _env_check() -> ValidationResult:
            return _check_environment_variables(vars_to_check)

        checks.append(_env_check)

    if extra_checks:
        checks.extend(extra_checks)

    results: list[ValidationResult] = []
    for check in checks:
        try:
            result = check()
        except Exception as exc:
            result = ValidationResult(
                component=check.__name__,
                status=ValidationStatus.FAIL,
                message=f"Check raised an exception: {exc}",
                remediation="Review the check implementation",
            )
        results.append(result)

    passed = sum(1 for r in results if r.status == ValidationStatus.PASS)
    failed = sum(1 for r in results if r.status == ValidationStatus.FAIL)

    return StartupValidationReport(
        results=tuple(results),
        all_passed=failed == 0,
        total=len(results),
        passed=passed,
        failed=failed,
    )


def assert_startup_validations(
    extra_checks: tuple[ValidationCheck, ...] | None = None,
    required_env_vars: tuple[str, ...] | None = None,
) -> StartupValidationReport:
    """Run validations and log results; exit if any check fails.

    Args:
        extra_checks:      Additional validation checks.
        required_env_vars: Required environment variable names.

    Returns:
        StartupValidationReport (only returned if all passed).

    Raises:
        SystemExit: If any critical validation fails.
    """
    report = run_startup_validations(
        extra_checks=extra_checks,
        required_env_vars=required_env_vars,
    )

    for result in report.results:
        if result.status == ValidationStatus.PASS:
            logger.info("  [PASS] %s — %s", result.component, result.message)
        else:
            msg = f"  [FAIL] {result.component} — {result.message}"
            if result.remediation:
                msg += f"\n         Remediation: {result.remediation}"
            logger.error(msg)

    if report.all_passed:
        logger.info(
            "Startup validation passed — %d/%d checks OK",
            report.passed,
            report.total,
        )
        return report

    logger.error(
        "Startup validation FAILED — %d/%d checks failed. Aborting.",
        report.failed,
        report.total,
    )
    sys.exit(1)
