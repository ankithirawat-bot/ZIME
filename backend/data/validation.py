"""
Data request and response validation.

Pure functions that return ValidationResult.  No exceptions
for expected validation failures.
"""

from __future__ import annotations

from backend.data.models import DataRequest, DataStatus, DataType, ValidationResult


def validate_request(request: DataRequest) -> ValidationResult:
    """Validate a DataRequest structurally.

    Checks:
        - symbol is non-empty
        - exchange is non-empty
        - start_date <= end_date
        - data_type is a valid DataType

    Args:
        request: The request to validate.

    Returns:
        ValidationResult with valid=True/False.
    """
    errors: list[str] = []
    warnings: list[str] = []
    missing: list[str] = []

    if not request.symbol or not request.symbol.strip():
        errors.append("Symbol must be non-empty")
        missing.append("symbol")

    if not request.exchange or not request.exchange.strip():
        errors.append("Exchange must be non-empty")
        missing.append("exchange")

    if request.start_date > request.end_date:
        errors.append(
            f"start_date ({request.start_date}) must be <= end_date ({request.end_date})"
        )

    if not isinstance(request.data_type, DataType):
        errors.append(f"Invalid data type: {request.data_type}")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        missing_fields=tuple(missing),
    )


def validate_response_data(
    payload: tuple[dict[str, object], ...],
    required_fields: tuple[str, ...] = (),
) -> ValidationResult:
    """Validate fetched data payload.

    Checks:
        - payload is non-empty
        - required fields are present in each row

    Args:
        payload:         Data rows.
        required_fields: Fields that must exist in each row.

    Returns:
        ValidationResult with valid=True/False.
    """
    errors: list[str] = []
    warnings: list[str] = []
    missing: list[str] = []

    if not payload:
        warnings.append("Empty payload returned")
        return ValidationResult(
            valid=True,
            errors=tuple(errors),
            warnings=tuple(warnings),
            missing_fields=tuple(missing),
        )

    if required_fields:
        first_row = payload[0]
        for field_name in required_fields:
            if field_name not in first_row:
                errors.append(f"Missing required field: {field_name}")
                missing.append(field_name)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        missing_fields=tuple(missing),
    )


def validate_status(status: DataStatus) -> bool:
    """Check if a response status indicates success.

    Args:
        status: Response status.

    Returns:
        True when status is SUCCESS or CACHED.
    """
    return status in (DataStatus.SUCCESS, DataStatus.CACHED)
