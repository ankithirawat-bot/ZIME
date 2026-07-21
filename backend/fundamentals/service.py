"""
Fundamentals service.

High-level orchestration over the FundamentalRepository: retrieval,
point-in-time lookup, latest snapshot assembly, and statement
aggregation for point-in-time research.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from backend.fundamentals.models import (
    FundamentalSnapshot,
    _FundamentalCommon,
)
from backend.fundamentals.repository import FundamentalRepository
from backend.fundamentals.types import StatementType


class FundamentalService:
    """Coordinates fundamental retrieval, point-in-time lookup and aggregation."""

    def __init__(self, repository: FundamentalRepository) -> None:
        """Initialise the service.

        Args:
            repository: FundamentalRepository for persistence.
        """
        self._repo = repository

    def retrieve(
        self, symbol: str, exchange: str, statement_type: StatementType
    ) -> tuple[object, ...]:
        """Retrieve all statements of a type for a symbol.

        Args:
            symbol:         Ticker symbol.
            exchange:       Exchange identifier.
            statement_type: Statement type.

        Returns:
            Tuple of statements ordered by fiscal period.
        """
        return self._repo.retrieve(symbol, exchange, statement_type)

    def retrieve_as_of(
        self,
        symbol: str,
        exchange: str,
        statement_type: StatementType,
        as_of: date,
    ) -> tuple[object, ...]:
        """Retrieve point-in-time effective statements.

        Args:
            symbol:         Ticker symbol.
            exchange:       Exchange identifier.
            statement_type: Statement type.
            as_of:          Reference date.

        Returns:
            Tuple of effective statements visible on as_of.
        """
        return self._repo.retrieve_as_of(symbol, exchange, statement_type, as_of)

    def latest_snapshot(
        self, symbol: str, exchange: str, as_of: date | None = None
    ) -> FundamentalSnapshot:
        """Assemble the latest effective statement per type.

        For each statement type the most recent fiscal period that is
        effective (as of the reference date) is selected.

        Args:
            symbol:   Ticker symbol.
            exchange: Exchange identifier.
            as_of:    Reference date (None = today, ignoring point-in-time).

        Returns:
            FundamentalSnapshot with the latest statement per type.
        """
        reference = as_of or date.today()
        statements: dict[StatementType, object] = {}
        for st in StatementType:
            if as_of is None:
                rows = self._repo.retrieve(symbol, exchange, st)
            else:
                rows = self._repo.retrieve_as_of(symbol, exchange, st, reference)
            if not rows:
                continue
            statements[st] = self._most_recent(rows)
        return FundamentalSnapshot(
            symbol=symbol, exchange=exchange, as_of=reference, statements=statements
        )

    def aggregate(
        self,
        symbol: str,
        exchange: str,
        statement_type: StatementType,
        metric: str,
        as_of: date | None = None,
    ) -> dict[int, Any]:
        """Aggregate a metric across fiscal periods.

        Args:
            symbol:         Ticker symbol.
            exchange:       Exchange identifier.
            statement_type: Statement type containing the metric.
            metric:         Metric key stored in each statement's data.
            as_of:          Optional point-in-time reference.

        Returns:
            Mapping of fiscal_year -> metric value, sorted by year.
        """
        if as_of is None:
            rows = self._repo.retrieve(symbol, exchange, statement_type)
        else:
            rows = self._repo.retrieve_as_of(symbol, exchange, statement_type, as_of)

        result: dict[int, Any] = {}
        for row in rows:
            value = row.data.get(metric) if hasattr(row, "data") else None
            if value is not None:
                result[row.fiscal_year] = value
        return dict(sorted(result.items()))

    def _most_recent(self, rows: tuple[object, ...]) -> object:
        def _sort_key(row: _FundamentalCommon):
            return (row.fiscal_year, row.fiscal_quarter or 0)

        return max(rows, key=_sort_key)
