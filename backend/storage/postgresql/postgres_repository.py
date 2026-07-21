"""
PostgreSQL Repository.

First production Repository implementation.
Persists normalized market data to PostgreSQL.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.storage.exceptions import (
    DatasetNotFoundError,
    DuplicateDatasetError,
    StorageError,
)
from backend.storage.models import (
    DatasetType,
    RetrievalRequest,
    RetrievalResult,
    StorageRequest,
    StorageResult,
)
from backend.storage.postgresql.connection import ConnectionManager
from backend.storage.postgresql.orm_models import DailyPrice, DatasetVersion, Symbol, UpdateLog
from backend.storage.repository import Repository


class PostgreSQLRepository(Repository):
    """Repository for PostgreSQL persistence of normalized market data.

    Stores only NormalizedData.  Never RawDataResponse.
    Every store() is atomic — rolls back on failure.
    """

    def __init__(self, conn_manager: ConnectionManager) -> None:
        """Initialise the PostgreSQL repository.

        Args:
            conn_manager: ConnectionManager for database access.
        """
        self._conn = conn_manager

    def store(self, request: StorageRequest) -> StorageResult:
        """Persist a dataset atomically.

        Args:
            request: Storage request with records.

        Returns:
            StorageResult with status.

        Raises:
            DuplicateDatasetError: If version already exists.
            StorageError: On database failure.
        """
        started_at = datetime.now(UTC)
        try:
            with self._conn.transaction() as session:
                symbol_id = self._ensure_symbol(session, request)

                version_str = request.version
                records_stored = 0
                warnings: list[str] = []

                for record in request.dataset:
                    self._store_price_record(
                        session,
                        symbol_id=symbol_id,
                        record=record,
                        provider=request.provider,
                    )
                    records_stored += 1

                self._store_version(
                    session,
                    request=request,
                    record_count=records_stored,
                )

                self._log_update(
                    session,
                    request=request,
                    record_count=records_stored,
                    status="success",
                    started_at=started_at,
                )

                storage_id = f"{request.provider}:{request.dataset_type.value}:{symbol_id}"

                return StorageResult(
                    success=True,
                    storage_id=storage_id,
                    version=version_str,
                    timestamp=datetime.now(UTC),
                    warnings=tuple(warnings),
                )

        except IntegrityError as exc:
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                raise DuplicateDatasetError(request.version) from exc
            raise StorageError(f"Database integrity error: {exc}") from exc

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Retrieve a dataset by symbol and date range.

        Args:
            request: Retrieval request.

        Returns:
            RetrievalResult with records and metadata.

        Raises:
            DatasetNotFoundError: If no data found.
        """
        with self._conn.session() as session:
            symbol = self._find_symbol(
                session,
                symbol=request.symbol,
                exchange="NSE",
            )
            if symbol is None:
                raise DatasetNotFoundError(
                    f"{request.dataset_type.value}:{request.symbol}"
                )

            query = (
                session.query(DailyPrice)
                .filter(
                    DailyPrice.symbol_id == symbol.id,
                    DailyPrice.trade_date >= datetime.combine(request.start_date, datetime.min.time()),
                    DailyPrice.trade_date <= datetime.combine(request.end_date, datetime.max.time()),
                )
                .order_by(DailyPrice.trade_date)
            )

            if request.version:
                query = query.filter(DailyPrice.version == request.version)

            prices = query.all()

            if not prices:
                raise DatasetNotFoundError(
                    f"{request.dataset_type.value}:{request.symbol}"
                )

            provider = prices[0].provider if prices else ""

            records = tuple(
                {
                    "date": p.trade_date.isoformat(),
                    "open": p.open,
                    "high": p.high,
                    "low": p.low,
                    "close": p.close,
                    "volume": p.volume,
                    "provider": p.provider,
                }
                for p in prices
            )

            return RetrievalResult(
                records=records,
                provider=provider,
                version=request.version or "",
                metadata={"record_count": str(len(records))},
            )

    def delete(self, dataset_type: DatasetType, symbol: str) -> bool:
        """Delete a dataset by symbol and type.

        Args:
            dataset_type: Type of dataset.
            symbol:       Ticker symbol.

        Returns:
            True if deleted successfully.
        """
        with self._conn.transaction() as session:
            sym = self._find_symbol(session, symbol=symbol, exchange="NSE")
            if sym is None:
                return False

            deleted = (
                session.query(DailyPrice)
                .filter(DailyPrice.symbol_id == sym.id)
                .delete()
            )

            self._log_update(
                session,
                request=StorageRequest(
                    dataset=(),
                    dataset_type=dataset_type,
                    provider="",
                    version="",
                ),
                record_count=deleted,
                status="deleted",
                started_at=datetime.now(UTC),
            )

            return deleted > 0

    def exists(self, dataset_type: DatasetType, symbol: str) -> bool:
        """Check if a dataset exists.

        Args:
            dataset_type: Type of dataset.
            symbol:       Ticker symbol.

        Returns:
            True if dataset exists.
        """
        with self._conn.session() as session:
            sym = self._find_symbol(session, symbol=symbol, exchange="NSE")
            if sym is None:
                return False

            count = (
                session.query(DailyPrice)
                .filter(DailyPrice.symbol_id == sym.id)
                .count()
            )
            return count > 0

    def supported_dataset_types(self) -> tuple[DatasetType, ...]:
        """Return dataset types this repository supports.

        Returns:
            Tuple of supported dataset types.
        """
        return (DatasetType.PRICE_DAILY,)

    def _ensure_symbol(
        self,
        session: Session,
        request: StorageRequest,
    ) -> int:
        """Ensure a symbol exists, creating if needed.

        Args:
            session: Database session.
            request: Storage request with symbol info.

        Returns:
            Symbol ID.
        """
        record = request.dataset[0] if request.dataset else {}
        symbol_str = str(record.get("symbol", request.metadata.get("symbol", "")))
        exchange = str(record.get("exchange", request.metadata.get("exchange", "NSE")))
        provider_symbol = str(record.get("provider_symbol", symbol_str))

        existing = self._find_symbol(session, symbol=symbol_str, exchange=exchange)
        if existing is not None:
            return existing.id

        new_symbol = Symbol(
            symbol=symbol_str,
            exchange=exchange,
            instrument_type="EQ",
            provider_symbol=provider_symbol,
        )
        session.add(new_symbol)
        session.flush()
        return new_symbol.id

    def _find_symbol(
        self,
        session: Session,
        symbol: str,
        exchange: str,
    ) -> Symbol | None:
        """Find a symbol by name and exchange.

        Args:
            session:  Database session.
            symbol:   Ticker symbol.
            exchange: Exchange identifier.

        Returns:
            Symbol or None.
        """
        return (
            session.query(Symbol)
            .filter(and_(Symbol.symbol == symbol, Symbol.exchange == exchange))
            .first()
        )

    def _store_price_record(
        self,
        session: Session,
        symbol_id: int,
        record: dict[str, object],
        provider: str,
    ) -> None:
        """Store a single price record.

        Args:
            session:   Database session.
            symbol_id: Symbol foreign key.
            record:    Price data dict.
            provider:  Provider name.
        """
        date_str = str(record.get("date", ""))
        dt = datetime.fromisoformat(date_str) if date_str else datetime.now(UTC)

        price = DailyPrice(
            symbol_id=symbol_id,
            trade_date=dt,
            open=float(record.get("open", 0.0)),
            high=float(record.get("high", 0.0)),
            low=float(record.get("low", 0.0)),
            close=float(record.get("close", 0.0)),
            volume=int(record.get("volume", 0)),
            provider=provider,
        )
        session.add(price)

    def _store_version(
        self,
        session: Session,
        request: StorageRequest,
        record_count: int,
    ) -> None:
        """Store version metadata.

        Args:
            session:      Database session.
            request:      Storage request.
            record_count: Number of records stored.
        """
        record = request.dataset[0] if request.dataset else {}
        symbol_str = str(record.get("symbol", request.metadata.get("symbol", "")))
        exchange = str(record.get("exchange", request.metadata.get("exchange", "NSE")))

        version = DatasetVersion(
            symbol=symbol_str,
            exchange=exchange,
            dataset_type=request.dataset_type.value,
            provider=request.provider,
            version=request.version,
            checksum=request.metadata.get("checksum", ""),
            record_count=record_count,
        )
        session.add(version)

    def _log_update(
        self,
        session: Session,
        request: StorageRequest,
        record_count: int,
        status: str = "success",
        started_at: datetime | None = None,
    ) -> None:
        """Log a storage operation.

        Args:
            session:      Database session.
            request:      Storage request.
            record_count: Number of records affected.
            status:       Operation status.
            started_at:   When the operation started.
        """
        record = request.dataset[0] if request.dataset else {}
        symbol_str = str(record.get("symbol", request.metadata.get("symbol", "")))
        exchange = str(record.get("exchange", request.metadata.get("exchange", "NSE")))

        start_date = None
        end_date = None
        if request.dataset:
            dates = [str(r.get("date", "")) for r in request.dataset if r.get("date")]
            if dates:
                try:
                    start_date = datetime.fromisoformat(min(dates))
                    end_date = datetime.fromisoformat(max(dates))
                except ValueError:
                    pass

        log_entry = UpdateLog(
            symbol=symbol_str,
            exchange=exchange,
            dataset_type=request.dataset_type.value,
            provider=request.provider,
            version=request.version,
            start_date=start_date,
            end_date=end_date,
            records_inserted=record_count,
            status=status,
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )
        session.add(log_entry)
