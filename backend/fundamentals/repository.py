"""
Fundamentals repository.

PostgreSQL-backed persistence and point-in-time retrieval for
company fundamentals. Raw statements are immutable; point-in-time
queries filter on effective_from/effective_to so historical research
never sees data that was not yet published.
"""

from __future__ import annotations

from datetime import date, datetime
from json import dumps, loads
from typing import Any

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.fundamentals.exceptions import DuplicateStatementError
from backend.fundamentals.models import (
    BalanceSheet,
    CashFlowStatement,
    CompanyProfile,
    FundamentalBatch,
    IncomeStatement,
    KeyRatios,
    ShareholdingPattern,
)
from backend.fundamentals.types import PeriodType, StatementType
from backend.storage.postgresql.connection import ConnectionManager
from backend.storage.postgresql.orm_models import (
    BalanceSheetORM,
    CashFlowORM,
    CompanyProfileORM,
    IncomeStatementORM,
    KeyRatiosORM,
    ShareholdingPatternORM,
    Symbol,
)

_COMMON_FIELDS = (
    "symbol",
    "exchange",
    "provider",
    "period_type",
    "fiscal_year",
    "report_date",
    "filing_date",
    "fiscal_quarter",
    "currency",
    "effective_from",
    "effective_to",
    "metadata",
)

_MODEL_TO_ORM = {
    CompanyProfile: CompanyProfileORM,
    IncomeStatement: IncomeStatementORM,
    BalanceSheet: BalanceSheetORM,
    CashFlowStatement: CashFlowORM,
    ShareholdingPattern: ShareholdingPatternORM,
    KeyRatios: KeyRatiosORM,
}

_STATEMENT_TO_MODEL = {
    StatementType.PROFILE: CompanyProfile,
    StatementType.INCOME_STATEMENT: IncomeStatement,
    StatementType.BALANCE_SHEET: BalanceSheet,
    StatementType.CASH_FLOW: CashFlowStatement,
    StatementType.SHAREHOLDING: ShareholdingPattern,
    StatementType.KEY_RATIOS: KeyRatios,
}

_STATEMENT_TO_ORM = {
    StatementType.PROFILE: CompanyProfileORM,
    StatementType.INCOME_STATEMENT: IncomeStatementORM,
    StatementType.BALANCE_SHEET: BalanceSheetORM,
    StatementType.CASH_FLOW: CashFlowORM,
    StatementType.SHAREHOLDING: ShareholdingPatternORM,
    StatementType.KEY_RATIOS: KeyRatiosORM,
}


class FundamentalRepository:
    """PostgreSQL-backed persistence for fundamental statements."""

    def __init__(self, conn_manager: ConnectionManager) -> None:
        """Initialise the repository.

        Args:
            conn_manager: ConnectionManager for database access.
        """
        self._conn = conn_manager

    def store(self, statement: object) -> object:
        """Persist a single fundamental statement.

        Args:
            statement: Validated fundamental model.

        Returns:
            The persisted statement.

        Raises:
            DuplicateStatementError: If an equivalent statement exists.
        """
        orm_cls = self._orm_for_model(statement)
        with self._conn.transaction() as session:
            symbol_id = self._ensure_symbol(session, statement)
            self._insert(session, symbol_id, orm_cls, statement)
        return statement

    def store_batch(self, batch: FundamentalBatch) -> int:
        """Persist every statement in a batch.

        Args:
            batch: Batch of validated fundamental statements.

        Returns:
            Number of statements stored.
        """
        stored = 0
        with self._conn.transaction() as session:
            for statement in batch.statements:
                orm_cls = self._orm_for_model(statement)
                symbol_id = self._ensure_symbol(session, statement)
                self._insert(session, symbol_id, orm_cls, statement)
                stored += 1
        return stored

    def retrieve(
        self, symbol: str, exchange: str, statement_type: StatementType
    ) -> tuple[object, ...]:
        """Retrieve all statements of a type for a symbol.

        Args:
            symbol:         Ticker symbol.
            exchange:       Exchange identifier.
            statement_type: Statement type to retrieve.

        Returns:
            Tuple of statements ordered by fiscal year/quarter.
        """
        orm_cls = _STATEMENT_TO_ORM[statement_type]
        model_cls = _STATEMENT_TO_MODEL[statement_type]
        with self._conn.session() as session:
            sym = self._find_symbol(session, symbol, exchange)
            if sym is None:
                return ()
            rows = (
                session.query(orm_cls)
                .filter(orm_cls.symbol_id == sym.id)
                .order_by(orm_cls.fiscal_year, orm_cls.fiscal_quarter)
                .all()
            )
            return tuple(
                self._to_model(r, model_cls, sym.symbol, sym.exchange) for r in rows
            )

    def retrieve_as_of(
        self,
        symbol: str,
        exchange: str,
        statement_type: StatementType,
        as_of: date,
    ) -> tuple[object, ...]:
        """Retrieve the point-in-time effective statements.

        Only rows whose effective_from <= as_of and (effective_to is
        NULL or effective_to >= as_of) are returned, so future
        restatements are never visible before their effective date.

        Args:
            symbol:         Ticker symbol.
            exchange:       Exchange identifier.
            statement_type: Statement type to retrieve.
            as_of:          Reference date for point-in-time lookup.

        Returns:
            Tuple of effective statements ordered by fiscal year/quarter.
        """
        orm_cls = _STATEMENT_TO_ORM[statement_type]
        model_cls = _STATEMENT_TO_MODEL[statement_type]
        as_of_dt = datetime(as_of.year, as_of.month, as_of.day)
        with self._conn.session() as session:
            sym = self._find_symbol(session, symbol, exchange)
            if sym is None:
                return ()
            rows = (
                session.query(orm_cls)
                .filter(
                    and_(
                        orm_cls.symbol_id == sym.id,
                        orm_cls.effective_from <= as_of_dt,
                        orm_cls.effective_to.is_(None)
                        | (orm_cls.effective_to >= as_of_dt),
                    )
                )
                .order_by(orm_cls.fiscal_year, orm_cls.fiscal_quarter)
                .all()
            )
            models = tuple(
                self._to_model(r, model_cls, sym.symbol, sym.exchange) for r in rows
            )
            return self._latest_revision_per_period(models)

    def exists(
        self, symbol: str, exchange: str, statement_type: StatementType
    ) -> bool:
        """Check whether any statement of a type exists for a symbol.

        Args:
            symbol:         Ticker symbol.
            exchange:       Exchange identifier.
            statement_type: Statement type to check.

        Returns:
            True if at least one matching statement exists.
        """
        orm_cls = _STATEMENT_TO_ORM[statement_type]
        with self._conn.session() as session:
            sym = self._find_symbol(session, symbol, exchange)
            if sym is None:
                return False
            return session.query(orm_cls).filter(orm_cls.symbol_id == sym.id).count() > 0

    def delete(
        self, symbol: str, exchange: str, statement_type: StatementType
    ) -> int:
        """Delete all statements of a type for a symbol.

        Args:
            symbol:         Ticker symbol.
            exchange:       Exchange identifier.
            statement_type: Statement type to delete.

        Returns:
            Number of statements deleted.
        """
        orm_cls = _STATEMENT_TO_ORM[statement_type]
        with self._conn.transaction() as session:
            sym = self._find_symbol(session, symbol, exchange)
            if sym is None:
                return 0
            return (
                session.query(orm_cls)
                .filter(orm_cls.symbol_id == sym.id)
                .delete()
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _orm_for_model(self, statement: object) -> type:
        orm_cls = _MODEL_TO_ORM.get(type(statement))
        if orm_cls is None:
            raise ValueError(f"Unsupported statement model: {type(statement).__name__}")
        return orm_cls

    def _latest_revision_per_period(
        self, models: tuple[object, ...]
    ) -> tuple[object, ...]:
        """Collapse restatements to the latest effective revision per period.

        Args:
            models: Effective statements visible on the reference date.

        Returns:
            One statement per (period_type, fiscal_year, fiscal_quarter),
            keeping the revision with the greatest effective_from.
        """
        best: dict[tuple[str, int, int], object] = {}
        for model in models:
            rec = model  # type: ignore[assignment]
            fq = rec.fiscal_quarter if rec.fiscal_quarter is not None else -1
            key = (rec.period_type.value, rec.fiscal_year, fq)
            current = best.get(key)
            if current is None or (rec.effective_from or rec.filing_date) > (
                current.effective_from or current.filing_date
            ):
                best[key] = rec
        return tuple(
            sorted(
                best.values(),
                key=lambda m: (m.fiscal_year, m.fiscal_quarter or 0),  # type: ignore[attr-defined]
            )
        )

    def _ensure_symbol(self, session: Session, statement: object) -> int:
        rec = statement  # type: ignore[assignment]
        existing = self._find_symbol(session, rec.symbol, rec.exchange)
        if existing is not None:
            return existing.id
        new_symbol = Symbol(
            symbol=rec.symbol,
            exchange=rec.exchange,
            instrument_type="EQ",
            provider_symbol=rec.symbol,
        )
        session.add(new_symbol)
        session.flush()
        return new_symbol.id

    def _find_symbol(
        self, session: Session, symbol: str, exchange: str
    ) -> Symbol | None:
        return (
            session.query(Symbol)
            .filter(and_(Symbol.symbol == symbol, Symbol.exchange == exchange))
            .first()
        )

    def _insert(
        self, session: Session, symbol_id: int, orm_cls: type, statement: object
    ) -> None:
        from dataclasses import fields

        rec = statement  # type: ignore[assignment]
        effective_from = rec.effective_from or rec.filing_date
        extra: dict[str, Any] = {}
        for f in fields(rec):
            if f.name not in _COMMON_FIELDS:
                extra[f.name] = getattr(rec, f.name)
        extra.update(rec.data)

        fiscal_quarter = rec.fiscal_quarter if rec.fiscal_quarter is not None else 0

        orm = orm_cls(  # type: ignore[call-arg]
            symbol_id=symbol_id,
            period_type=rec.period_type.value,
            fiscal_year=rec.fiscal_year,
            fiscal_quarter=fiscal_quarter,
            report_date=datetime(rec.report_date.year, rec.report_date.month, rec.report_date.day),
            filing_date=datetime(rec.filing_date.year, rec.filing_date.month, rec.filing_date.day),
            currency=rec.currency,
            provider=rec.provider,
            effective_from=datetime(effective_from.year, effective_from.month, effective_from.day),
            effective_to=(
                datetime(rec.effective_to.year, rec.effective_to.month, rec.effective_to.day)
                if rec.effective_to is not None
                else None
            ),
            metadata_json=dumps(rec.metadata or {}, default=str),
            data_json=dumps(extra, default=str),
        )
        try:
            session.add(orm)
            session.flush()
        except IntegrityError as exc:
            fq = rec.fiscal_quarter if rec.fiscal_quarter is not None else "NA"
            raise DuplicateStatementError(
                rec.symbol,
                rec.period_type.value,
                f"{rec.fiscal_year}:{fq}",
            ) from exc

    def _to_model(
        self, row: object, model_cls: type, symbol: str, exchange: str
    ) -> object:
        from dataclasses import fields

        r = row  # type: ignore[assignment]
        data: dict[str, Any] = {}
        if r.data_json:
            try:
                data = loads(r.data_json)
            except (ValueError, TypeError):
                data = {}

        specific_keys = {
            f.name for f in fields(model_cls) if f.name not in _COMMON_FIELDS
        }
        specific = {
            k: data.get(k, "")
            for k in specific_keys
            if k != "data"
        }
        metrics = {k: v for k, v in data.items() if k not in specific_keys}

        metadata: dict[str, Any] = {}
        if r.metadata_json:
            try:
                metadata = loads(r.metadata_json)
            except (ValueError, TypeError):
                metadata = {}

        return model_cls(  # type: ignore[call-arg]
            symbol=symbol,
            exchange=exchange,
            provider=r.provider,
            period_type=PeriodType(r.period_type),
            fiscal_year=r.fiscal_year,
            report_date=r.report_date.date(),
            filing_date=r.filing_date.date(),
            fiscal_quarter=r.fiscal_quarter if r.fiscal_quarter else None,
            currency=r.currency,
            effective_from=r.effective_from.date(),
            effective_to=r.effective_to.date() if r.effective_to is not None else None,
            metadata=metadata,
            data=metrics,
            **specific,
        )
