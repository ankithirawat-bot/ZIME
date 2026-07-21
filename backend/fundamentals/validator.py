"""
Fundamentals validator.

Validates fundamental records and rejects invalid ones.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.fundamentals.exceptions import (
    InvalidFundamentalError,
    UnsupportedStatementTypeError,
)
from backend.fundamentals.models import (
    FundamentalBatch,
    ShareholdingPattern,
    _FundamentalCommon,
)
from backend.fundamentals.types import PeriodType


@dataclass(frozen=True)
class ValidationReport:
    """Outcome of validating fundamental statements.

    Attributes:
        valid:          True when all statements are valid.
        valid_records:  Statements that passed validation.
        errors:         Blocking error messages.
        duplicate_keys: Detected duplicate identifiers.
    """

    valid: bool
    valid_records: tuple[object, ...]
    errors: tuple[str, ...]
    duplicate_keys: tuple[str, ...]


class FundamentalValidator:
    """Validates fundamental statements."""

    def validate_batch(self, batch: FundamentalBatch) -> ValidationReport:
        """Validate every statement in a batch.

        Args:
            batch: Batch of fundamental statements.

        Returns:
            ValidationReport with valid records and errors.
        """
        errors: list[str] = []
        valid_records: list[object] = []
        seen: set[str] = set()
        duplicate_keys: list[str] = []

        for record in batch.statements:
            try:
                self.validate(record)
            except (
                InvalidFundamentalError,
                UnsupportedStatementTypeError,
            ) as exc:
                errors.append(str(exc))
                continue

            key = self._identity_key(record)
            if key in seen:
                dup = key
                errors.append(f"Duplicate fundamental statement: {dup}")
                duplicate_keys.append(dup)
                continue

            seen.add(key)
            valid_records.append(record)

        return ValidationReport(
            valid=len(errors) == 0,
            valid_records=tuple(valid_records),
            errors=tuple(errors),
            duplicate_keys=tuple(duplicate_keys),
        )

    def validate(self, record: object) -> None:
        """Validate a single fundamental statement.

        Raises:
            InvalidFundamentalError:        On malformed fields.
            UnsupportedStatementTypeError: On unknown statement type.
        """
        if not isinstance(record, _FundamentalCommon):
            raise InvalidFundamentalError("Record is not a fundamental statement")

        if not record.symbol:
            raise InvalidFundamentalError("Fundamental record missing symbol")
        if not record.exchange:
            raise InvalidFundamentalError("Fundamental record missing exchange")
        if not record.provider:
            raise InvalidFundamentalError("Fundamental record missing provider")

        self._validate_period(record)
        self._validate_dates(record)
        self._validate_currency(record)
        self._validate_values(record)

    def _validate_period(self, record: _FundamentalCommon) -> None:
        if record.period_type not in PeriodType:
            raise UnsupportedStatementTypeError(record.period_type.value)
        if record.fiscal_year <= 0 or record.fiscal_year > 9999:
            raise InvalidFundamentalError(
                f"{record.symbol}: invalid fiscal_year {record.fiscal_year}"
            )
        if record.fiscal_quarter is not None:
            if record.fiscal_quarter < 1 or record.fiscal_quarter > 4:
                raise InvalidFundamentalError(
                    f"{record.symbol}: fiscal_quarter must be 1-4, got {record.fiscal_quarter}"
                )

    def _validate_dates(self, record: _FundamentalCommon) -> None:
        if record.filing_date < record.report_date:
            raise InvalidFundamentalError(
                f"{record.symbol}: filing_date {record.filing_date} precedes "
                f"report_date {record.report_date}"
            )
        if record.effective_from is not None and record.effective_to is not None:
            if record.effective_to < record.effective_from:
                raise InvalidFundamentalError(
                    f"{record.symbol}: effective_to precedes effective_from"
                )

    def _validate_currency(self, record: _FundamentalCommon) -> None:
        if not record.currency or len(record.currency) > 10:
            raise InvalidFundamentalError(
                f"{record.symbol}: invalid currency {record.currency!r}"
            )

    def _validate_values(self, record: _FundamentalCommon) -> None:
        for key, value in record.data.items():
            if isinstance(value, (int, float)) and value != value:  # NaN check
                raise InvalidFundamentalError(
                    f"{record.symbol}: impossible NaN value for {key}"
                )
            if key.endswith("_pct") or key.endswith("_ratio"):
                if isinstance(value, (int, float)) and (value < -1000 or value > 1e9):
                    raise InvalidFundamentalError(
                        f"{record.symbol}: implausible value for {key}: {value}"
                    )
        self._validate_statement_specific(record)

    def _validate_statement_specific(self, record: _FundamentalCommon) -> None:
        if isinstance(record, ShareholdingPattern):
            total = sum(
                float(record.data.get(k, 0) or 0)
                for k in ("promoter", "fii", "dii", "public")
            )
            if total > 100.5:
                raise InvalidFundamentalError(
                    f"{record.symbol}: shareholding percentages sum to {total} (>100)"
                )

    def _identity_key(self, record: object) -> str:
        rec = record  # type: ignore[assignment]
        fq = rec.fiscal_quarter if rec.fiscal_quarter is not None else "NA"
        return (
            f"{rec.symbol}:{rec.exchange}:{rec.period_type.value}:"
            f"{rec.fiscal_year}:{fq}:{rec.provider}"
        )

    def detect_duplicates(self, records: tuple[object, ...]) -> list[str]:
        """Return identifiers of duplicate statements within a collection.

        Args:
            records: Fundamental statements to inspect.

        Returns:
            List of duplicate identity keys (first occurrence excluded).
        """
        seen: set[str] = set()
        duplicates: list[str] = []
        for record in records:
            key = self._identity_key(record)
            if key in seen:
                duplicates.append(key)
            else:
                seen.add(key)
        return duplicates
