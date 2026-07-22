"""
Fundamentals normalizer.

Converts provider-specific payloads into canonical immutable
fundamental models. Provider-specific field names MUST NOT leak
outside this layer.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from backend.core.constants import DEFAULT_EXCHANGE
from backend.fundamentals.exceptions import UnsupportedStatementTypeError
from backend.fundamentals.models import (
    BalanceSheet,
    CashFlowStatement,
    CompanyProfile,
    IncomeStatement,
    KeyRatios,
    ShareholdingPattern,
)
from backend.fundamentals.types import PeriodType, StatementType


class FundamentalNormalizer:
    """Translates provider payloads into canonical models."""

    _MODEL_MAP: dict[str, type] = {
        StatementType.PROFILE.value: CompanyProfile,
        StatementType.INCOME_STATEMENT.value: IncomeStatement,
        StatementType.BALANCE_SHEET.value: BalanceSheet,
        StatementType.CASH_FLOW.value: CashFlowStatement,
        StatementType.SHAREHOLDING.value: ShareholdingPattern,
        StatementType.KEY_RATIOS.value: KeyRatios,
    }

    def normalize(
        self, payload: dict[str, Any], provider: str, statement_type: StatementType | None = None
    ) -> object:
        """Normalize a single provider payload.

        Args:
            payload: Provider-specific raw record.
            provider: Originating provider name.
            statement_type: Explicit type; if omitted it is read from payload.

        Returns:
            Canonical fundamental model.

        Raises:
            UnsupportedStatementTypeError: If statement type is unknown.
            ValueError: If required fields are missing or malformed.
        """
        raw_type = payload.get("statement_type") or payload.get("type")
        if statement_type is not None:
            resolved = statement_type
        elif raw_type is not None:
            resolved = self._resolve_type(str(raw_type))
        else:
            raise ValueError("Missing statement_type in payload")

        model_cls = self._MODEL_MAP.get(resolved.value)
        if model_cls is None:
            raise UnsupportedStatementTypeError(resolved.value)

        symbol = payload.get("symbol")
        exchange = payload.get("exchange", DEFAULT_EXCHANGE)
        if not symbol:
            raise ValueError("Missing symbol in payload")

        period_type = self._resolve_period(str(payload.get("period_type", "annual")))
        fiscal_year = int(payload.get("fiscal_year", 0))
        if fiscal_year <= 0:
            raise ValueError("Missing or invalid fiscal_year in payload")

        fiscal_quarter = payload.get("fiscal_quarter")
        fiscal_quarter = int(fiscal_quarter) if fiscal_quarter not in (None, "") else None

        report_date = self._parse_date(payload.get("report_date") or payload.get("period_end"))
        filing_date = self._parse_date(payload.get("filing_date") or payload.get("published_date"))
        if report_date is None:
            raise ValueError("Missing report_date in payload")
        if filing_date is None:
            raise ValueError("Missing filing_date in payload")

        currency = str(payload.get("currency", "INR"))
        effective_from = self._parse_date(payload.get("effective_from"))
        effective_to = self._parse_date(payload.get("effective_to"))

        raw_metadata = payload.get("metadata", {})
        if not isinstance(raw_metadata, dict):
            raw_metadata = {}

        data = dict(payload.get("data", {}))
        extra = {
            k: v
            for k, v in payload.items()
            if k
            not in (
                "symbol", "exchange", "provider", "statement_type", "type",
                "period_type", "fiscal_year", "fiscal_quarter", "report_date",
                "period_end", "filing_date", "published_date", "currency",
                "effective_from", "effective_to", "metadata", "data",
            )
        }
        data.update(extra)

        if model_cls is CompanyProfile:
            return CompanyProfile(
                symbol=str(symbol),
                exchange=str(exchange),
                provider=provider,
                period_type=period_type,
                fiscal_year=fiscal_year,
                report_date=report_date,
                filing_date=filing_date,
                fiscal_quarter=fiscal_quarter,
                currency=currency,
                effective_from=effective_from,
                effective_to=effective_to,
                metadata=dict(raw_metadata),
                data=data,
                name=str(payload.get("name", "")),
                sector=str(payload.get("sector", "")),
                industry=str(payload.get("industry", "")),
            )

        return model_cls(  # type: ignore[call-arg]
            symbol=str(symbol),
            exchange=str(exchange),
            provider=provider,
            period_type=period_type,
            fiscal_year=fiscal_year,
            report_date=report_date,
            filing_date=filing_date,
            fiscal_quarter=fiscal_quarter,
            currency=currency,
            effective_from=effective_from,
            effective_to=effective_to,
            metadata=dict(raw_metadata),
            data=data,
        )

    def _resolve_type(self, raw_type: str) -> StatementType:
        key = raw_type.strip().lower()
        for st in StatementType:
            if st.value == key or st.name.lower() == key:
                return st
        raise UnsupportedStatementTypeError(raw_type)

    def _resolve_period(self, raw_period: str) -> PeriodType:
        key = raw_period.strip().lower()
        mapping = {
            "annual": PeriodType.ANNUAL,
            "yearly": PeriodType.ANNUAL,
            "fy": PeriodType.ANNUAL,
            "quarterly": PeriodType.QUARTERLY,
            "quarter": PeriodType.QUARTERLY,
            "q": PeriodType.QUARTERLY,
            "ttm": PeriodType.TTM,
            "interim": PeriodType.INTERIM,
        }
        mapped = mapping.get(key)
        if mapped is None:
            return PeriodType.ANNUAL
        return mapped

    def _parse_date(self, value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return date.fromisoformat(value[:10])
        raise ValueError(f"Unrecognized date value: {value!r}")
