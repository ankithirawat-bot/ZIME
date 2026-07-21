"""
Price Validator.

Validates OHLCV data quality for provider responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ValidationResult:
    """Result of price data validation.

    Attributes:
        valid:    True when all checks pass.
        errors:   Blocking validation errors.
        warnings: Non-blocking observations.
    """

    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


class PriceValidator:
    """Validates OHLCV candle data quality.

    Checks:
        - Date ordering
        - Duplicate timestamps
        - Missing OHLC values
        - High >= Open, High >= Close
        - Low <= Open, Low <= Close
        - Volume >= 0
        - No future dates
    """

    def validate(self, candles: tuple[dict[str, object], ...]) -> ValidationResult:
        """Validate a tuple of candle records.

        Args:
            candles: Candle records with timestamp, open, high, low, close, volume.

        Returns:
            ValidationResult with errors and warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not candles:
            warnings.append("Empty candle data")
            return ValidationResult(valid=True, warnings=tuple(warnings))

        seen_timestamps: set[str] = set()
        today = date.today()

        for idx, candle in enumerate(candles):
            prefix = f"Candle {idx}"

            open_val = candle.get("open")
            high_val = candle.get("high")
            low_val = candle.get("low")
            close_val = candle.get("close")
            volume_val = candle.get("volume")
            timestamp = candle.get("timestamp", "")

            missing = [
                name
                for name, val in [
                    ("open", open_val),
                    ("high", high_val),
                    ("low", low_val),
                    ("close", close_val),
                ]
                if val is None
            ]
            if missing:
                errors.append(f"{prefix}: missing {', '.join(missing)}")
                continue

            assert open_val is not None
            assert high_val is not None
            assert low_val is not None
            assert close_val is not None

            if not isinstance(open_val, (int, float)):
                errors.append(f"{prefix}: open is not numeric")
                continue
            if not isinstance(high_val, (int, float)):
                errors.append(f"{prefix}: high is not numeric")
                continue
            if not isinstance(low_val, (int, float)):
                errors.append(f"{prefix}: low is not numeric")
                continue
            if not isinstance(close_val, (int, float)):
                errors.append(f"{prefix}: close is not numeric")
                continue

            if high_val < open_val:
                errors.append(f"{prefix}: high ({high_val}) < open ({open_val})")
            if high_val < close_val:
                errors.append(f"{prefix}: high ({high_val}) < close ({close_val})")
            if low_val > open_val:
                errors.append(f"{prefix}: low ({low_val}) > open ({open_val})")
            if low_val > close_val:
                errors.append(f"{prefix}: low ({low_val}) > close ({close_val})")

            if volume_val is not None and isinstance(volume_val, (int, float)):
                if volume_val < 0:
                    errors.append(f"{prefix}: negative volume ({volume_val})")
            elif volume_val is None:
                warnings.append(f"{prefix}: missing volume")

            if isinstance(timestamp, str) and timestamp:
                if timestamp in seen_timestamps:
                    errors.append(f"{prefix}: duplicate timestamp ({timestamp})")
                seen_timestamps.add(timestamp)

                try:
                    ts_date = _parse_timestamp_date(timestamp)
                    if ts_date > today:
                        errors.append(f"{prefix}: future date ({timestamp})")
                except ValueError:
                    warnings.append(f"{prefix}: unparseable timestamp ({timestamp})")

        if candles:
            timestamps = [c.get("timestamp", "") for c in candles]
            if timestamps and timestamps != sorted(timestamps):
                warnings.append("Candles not in chronological order")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )


def _parse_timestamp_date(timestamp: str) -> date:
    """Extract date from ISO-8601 timestamp.

    Args:
        timestamp: ISO-8601 timestamp string.

    Returns:
        Parsed date.

    Raises:
        ValueError: If timestamp cannot be parsed.
    """
    clean = timestamp.split("T")[0]
    parts = clean.split("-")
    if len(parts) != 3:
        raise ValueError(f"Invalid date format: {timestamp}")
    return date(int(parts[0]), int(parts[1]), int(parts[2]))
