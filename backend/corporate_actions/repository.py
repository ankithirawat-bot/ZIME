"""
Corporate Actions repository.

Persists validated corporate actions to PostgreSQL via the shared
ConnectionManager. Raw price data lives in a separate table and is
never mutated by this repository.
"""

from __future__ import annotations

from datetime import datetime
from json import dumps, loads
from typing import Any

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.corporate_actions.exceptions import DuplicateActionError
from backend.corporate_actions.models import (
    CorporateAction,
    CorporateActionBatch,
)
from backend.corporate_actions.types import ActionType
from backend.storage.postgresql.connection import ConnectionManager
from backend.storage.postgresql.orm_models import CorporateAction as CorporateActionORM
from backend.storage.postgresql.orm_models import Symbol


class CorporateActionRepository:
    """PostgreSQL-backed persistence for corporate actions."""

    def __init__(self, conn_manager: ConnectionManager) -> None:
        """Initialise the repository.

        Args:
            conn_manager: ConnectionManager for database access.
        """
        self._conn = conn_manager

    def store(self, action: CorporateAction) -> CorporateAction:
        """Persist a single corporate action.

        Args:
            action: Validated corporate action.

        Returns:
            The persisted CorporateAction.

        Raises:
            DuplicateActionError: If the same event already exists.
            StorageError: On database failure.
        """
        with self._conn.transaction() as session:
            symbol_id = self._ensure_symbol(session, action)
            self._insert(session, symbol_id, action)
        return action

    def store_batch(self, batch: CorporateActionBatch) -> int:
        """Persist every action in a batch.

        Args:
            batch: Batch of validated corporate actions.

        Returns:
            Number of actions stored.
        """
        stored = 0
        with self._conn.transaction() as session:
            for action in batch.actions:
                symbol_id = self._ensure_symbol(session, action)
                self._insert(session, symbol_id, action)
                stored += 1
        return stored

    def get_for_symbol(
        self, symbol: str, exchange: str = "NSE"
    ) -> tuple[CorporateAction, ...]:
        """Retrieve all corporate actions for a symbol.

        Args:
            symbol:   Ticker symbol.
            exchange: Exchange identifier.

        Returns:
            Tuple of CorporateAction ordered by effective date.
        """
        with self._conn.session() as session:
            sym = self._find_symbol(session, symbol, exchange)
            if sym is None:
                return ()
            rows = (
                session.query(CorporateActionORM)
                .filter(CorporateActionORM.symbol_id == sym.id)
                .order_by(CorporateActionORM.effective_date)
                .all()
            )
            return tuple(
                self._to_model(r, sym.symbol, sym.exchange) for r in rows
            )

    def exists(
        self,
        symbol: str,
        action_type: ActionType,
        effective_date: datetime.date,
        provider: str,
        exchange: str = "NSE",
    ) -> bool:
        """Check whether an equivalent action already exists.

        Args:
            symbol:        Ticker symbol.
            action_type:   Action type.
            effective_date: Effective date.
            provider:      Provider name.
            exchange:      Exchange identifier.

        Returns:
            True if a matching action is persisted.
        """
        with self._conn.session() as session:
            sym = self._find_symbol(session, symbol, exchange)
            if sym is None:
                return False
            count = (
                session.query(CorporateActionORM)
                .filter(
                    and_(
                        CorporateActionORM.symbol_id == sym.id,
                        CorporateActionORM.action_type == action_type.value,
                        CorporateActionORM.effective_date
                        == datetime(effective_date.year, effective_date.month, effective_date.day),
                        CorporateActionORM.provider == provider,
                    )
                )
                .count()
            )
            return count > 0

    def _ensure_symbol(self, session: Session, action: CorporateAction) -> int:
        existing = self._find_symbol(session, action.symbol, action.exchange)
        if existing is not None:
            return existing.id
        new_symbol = Symbol(
            symbol=action.symbol,
            exchange=action.exchange,
            instrument_type="EQ",
            provider_symbol=action.symbol,
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
        self, session: Session, symbol_id: int, action: CorporateAction
    ) -> None:
        from datetime import datetime as _dt

        orm = CorporateActionORM(
            symbol_id=symbol_id,
            action_type=action.action_type.value,
            effective_date=_dt(
                action.effective_date.year,
                action.effective_date.month,
                action.effective_date.day,
            ),
            ratio=action.ratio,
            cash_amount=action.cash_amount,
            currency=action.currency,
            provider=action.provider,
            description=action.description,
            metadata_json=dumps(action.metadata or {}, default=str),
        )
        try:
            session.add(orm)
            session.flush()
        except IntegrityError as exc:
            raise DuplicateActionError(
                action.symbol,
                action.action_type.value,
                action.effective_date.isoformat(),
            ) from exc

    def _to_model(
        self, row: CorporateActionORM, symbol: str, exchange: str
    ) -> CorporateAction:
        raw_metadata: dict[str, Any] = {}
        if row.metadata_json:
            try:
                raw_metadata = loads(row.metadata_json)
            except (ValueError, TypeError):
                raw_metadata = {}
        return CorporateAction(
            symbol=symbol,
            exchange=exchange,
            action_type=ActionType(row.action_type),
            effective_date=row.effective_date.date(),
            provider=row.provider,
            ratio=row.ratio,
            cash_amount=row.cash_amount,
            currency=row.currency,
            description=row.description,
            metadata=raw_metadata,
        )
