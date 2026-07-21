"""Pipeline stage executor.

Implements the execution flow for each pipeline stage:
Fetch → Validate → Normalize → Corporate Action → Data Quality → Persist
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any

from backend.data.models import DataRequest, DataResponse, DataStatus, DataType
from backend.data_quality.models import PriceBar, ValidationRequest
from backend.pipeline.models import StageName, StageResult
from backend.storage.models import DatasetType, StorageRequest

from .pipeline_context import PipelineContext


class PipelineExecutor:
    """Executes individual pipeline stages.

    Each stage is independently testable and can be skipped
    via pipeline configuration.
    """

    def __init__(self, context: PipelineContext) -> None:
        self._context = context

    def execute_fetch(
        self, symbol: str, exchange: str, start_date: date, end_date: date
    ) -> StageResult:
        """Execute the fetch stage.

        Args:
            symbol:      Ticker symbol.
            exchange:    Exchange identifier.
            start_date:  Start date for data request.
            end_date:    End date for data request.

        Returns:
            StageResult with fetched data in metadata.
        """
        start = time.monotonic()
        try:
            request = DataRequest(
                symbol=symbol,
                exchange=exchange,
                data_type=DataType.PRICE_DAILY,
                start_date=start_date,
                end_date=end_date,
            )
            response = self._context.data_engine.get_data(request)

            if response.status is DataStatus.FAILED:
                return StageResult(
                    stage=StageName.FETCH,
                    success=False,
                    duration=time.monotonic() - start,
                    message=f"Provider returned FAILED status for {symbol}",
                )

            return StageResult(
                stage=StageName.FETCH,
                success=True,
                duration=time.monotonic() - start,
                message=f"Fetched {len(response.payload)} records for {symbol}",
                metadata={"response": response},
            )
        except Exception as e:
            return StageResult(
                stage=StageName.FETCH,
                success=False,
                duration=time.monotonic() - start,
                message=f"Fetch failed for {symbol}: {e}",
            )

    def execute_validate(
        self, symbol: str, exchange: str, response: DataResponse
    ) -> StageResult:
        """Execute the validate stage.

        Args:
            symbol:   Ticker symbol.
            exchange: Exchange identifier.
            response: Data response to validate.

        Returns:
            StageResult with validation results.
        """
        start = time.monotonic()
        try:
            bars = self._convert_to_bars(response.payload)
            if not bars:
                return StageResult(
                    stage=StageName.VALIDATE,
                    success=True,
                    duration=time.monotonic() - start,
                    message=f"No bars to validate for {symbol}",
                    metadata={"bars": (), "validation_result": None},
                )

            request = ValidationRequest(
                symbol=symbol,
                exchange=exchange,
                provider=response.provider,
                bars=tuple(bars),
            )
            result = self._context.validator.validate(request)

            return StageResult(
                stage=StageName.VALIDATE,
                success=result.is_valid,
                duration=time.monotonic() - start,
                message=f"Validation {'passed' if result.is_valid else 'failed'} for {symbol}",
                metadata={"bars": tuple(bars), "validation_result": result},
            )
        except Exception as e:
            return StageResult(
                stage=StageName.VALIDATE,
                success=False,
                duration=time.monotonic() - start,
                message=f"Validation error for {symbol}: {e}",
            )

    def execute_normalize(
        self, symbol: str, response: DataResponse, bars: tuple[PriceBar, ...]
    ) -> StageResult:
        """Execute the normalize stage.

        Converts PriceBar tuples to storage-ready dictionaries.

        Args:
            symbol:   Ticker symbol.
            response: Original data response.
            bars:     Validated price bars.

        Returns:
            StageResult with normalized records.
        """
        start = time.monotonic()
        try:
            records = self._bars_to_records(bars, symbol, response.request.exchange)

            return StageResult(
                stage=StageName.NORMALIZE,
                success=True,
                duration=time.monotonic() - start,
                message=f"Normalized {len(records)} records for {symbol}",
                metadata={"records": records},
            )
        except Exception as e:
            return StageResult(
                stage=StageName.NORMALIZE,
                success=False,
                duration=time.monotonic() - start,
                message=f"Normalization failed for {symbol}: {e}",
            )

    def execute_corporate_action(
        self,
        symbol: str,
        exchange: str,
        records: tuple[dict[str, Any], ...],
    ) -> StageResult:
        """Execute the corporate action adjustment stage.

        Args:
            symbol:   Ticker symbol.
            exchange: Exchange identifier.
            records:  Raw price records.

        Returns:
            StageResult with adjusted records.
        """
        start = time.monotonic()
        try:
            from backend.corporate_actions.models import AdjustmentRequest

            request = AdjustmentRequest(
                symbol=symbol,
                exchange=exchange,
                raw_prices=records,
                actions=(),
            )
            result = self._context.adjustment_engine.adjust_prices(request)

            adjusted_records = self._adjusted_prices_to_records(
                result.prices, symbol, exchange
            )

            return StageResult(
                stage=StageName.CORPORATE_ACTION,
                success=True,
                duration=time.monotonic() - start,
                message=f"Applied {len(result.actions_applied)} corporate actions for {symbol}",
                metadata={"records": adjusted_records, "actions_applied": len(result.actions_applied)},
            )
        except Exception as e:
            return StageResult(
                stage=StageName.CORPORATE_ACTION,
                success=False,
                duration=time.monotonic() - start,
                message=f"Corporate action adjustment failed for {symbol}: {e}",
            )

    def execute_data_quality(
        self, symbol: str, exchange: str, bars: tuple[PriceBar, ...]
    ) -> StageResult:
        """Execute the data quality check stage.

        Args:
            symbol:   Ticker symbol.
            exchange: Exchange identifier.
            bars:     Price bars to check.

        Returns:
            StageResult with anomaly count.
        """
        start = time.monotonic()
        try:
            if not bars:
                return StageResult(
                    stage=StageName.DATA_QUALITY,
                    success=True,
                    duration=time.monotonic() - start,
                    message=f"No bars to check for {symbol}",
                    metadata={"anomalies": 0},
                )

            anomalies = self._context.anomaly_detector.detect(
                bars, symbol, exchange, "upstox"
            )

            return StageResult(
                stage=StageName.DATA_QUALITY,
                success=True,
                duration=time.monotonic() - start,
                message=f"Detected {len(anomalies)} anomalies for {symbol}",
                metadata={"anomalies": len(anomalies)},
            )
        except Exception as e:
            return StageResult(
                stage=StageName.DATA_QUALITY,
                success=False,
                duration=time.monotonic() - start,
                message=f"Data quality check failed for {symbol}: {e}",
            )

    def execute_persist(
        self, symbol: str, exchange: str, records: tuple[dict[str, Any], ...]
    ) -> StageResult:
        """Execute the persist stage.

        Args:
            symbol:   Ticker symbol.
            exchange: Exchange identifier.
            records:  Records to persist.

        Returns:
            StageResult with persistence results.
        """
        start = time.monotonic()
        try:
            if not records:
                return StageResult(
                    stage=StageName.PERSIST,
                    success=True,
                    duration=time.monotonic() - start,
                    message=f"No records to persist for {symbol}",
                    metadata={"inserted": 0, "updated": 0},
                )

            storage_request = StorageRequest(
                dataset=records,
                dataset_type=DatasetType.PRICE_DAILY,
                provider="upstox",
                version=f"{symbol}:{date.today().isoformat()}",
                metadata={"symbol": symbol, "exchange": exchange},
            )
            result = self._context.repository.store(storage_request)

            return StageResult(
                stage=StageName.PERSIST,
                success=result.success,
                duration=time.monotonic() - start,
                message=f"Persisted {len(records)} records for {symbol}",
                metadata={"inserted": len(records), "updated": 0, "storage_id": result.storage_id},
            )
        except Exception as e:
            return StageResult(
                stage=StageName.PERSIST,
                success=False,
                duration=time.monotonic() - start,
                message=f"Persistence failed for {symbol}: {e}",
            )

    def _convert_to_bars(self, payload: tuple[dict[str, object], ...]) -> tuple[PriceBar, ...]:
        """Convert payload dictionaries to PriceBar objects."""
        bars: list[PriceBar] = []
        for record in payload:
            try:
                trade_date = record.get("trade_date") or record.get("date")
                if isinstance(trade_date, str):
                    from datetime import datetime as dt
                    trade_date = dt.fromisoformat(trade_date).date()

                bar = PriceBar(
                    trade_date=trade_date,
                    open=float(record.get("open", 0)),
                    high=float(record.get("high", 0)),
                    low=float(record.get("low", 0)),
                    close=float(record.get("close", 0)),
                    volume=float(record.get("volume", 0)),
                    adjusted_close=record.get("adjusted_close"),
                )
                bars.append(bar)
            except (ValueError, TypeError):
                continue
        return tuple(bars)

    def _bars_to_records(
        self, bars: tuple[PriceBar, ...], symbol: str, exchange: str
    ) -> tuple[dict[str, Any], ...]:
        """Convert PriceBar objects to storage-ready dictionaries."""
        records: list[dict[str, Any]] = []
        for bar in bars:
            record: dict[str, Any] = {
                "date": bar.trade_date.isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": int(bar.volume),
                "symbol": symbol,
                "exchange": exchange,
            }
            if bar.adjusted_close is not None:
                record["adjusted_close"] = bar.adjusted_close
            records.append(record)
        return tuple(records)

    def _adjusted_prices_to_records(
        self,
        prices: tuple[Any, ...],
        symbol: str,
        exchange: str,
    ) -> tuple[dict[str, Any], ...]:
        """Convert adjusted prices to storage-ready dictionaries."""
        records: list[dict[str, Any]] = []
        for price in prices:
            record: dict[str, Any] = {
                "date": price.trade_date.isoformat(),
                "open": price.open,
                "high": price.high,
                "low": price.low,
                "close": price.close,
                "volume": int(price.volume),
                "symbol": symbol,
                "exchange": exchange,
                "adjusted_close": price.adjusted_close,
                "factor": price.factor,
            }
            records.append(record)
        return tuple(records)
