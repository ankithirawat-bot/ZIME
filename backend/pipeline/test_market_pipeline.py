"""
Market data pipeline tests.

Covers pipeline execution, validation failures, provider failures,
persistence failures, multiple symbols, empty datasets, and report
correctness.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.bootstrap.pipeline_bootstrap import create_default_pipeline
from backend.data.models import DataRequest, DataResponse, DataStatus, DataType
from backend.data_quality.anomaly_detector import AnomalyDetectorEngine
from backend.data_quality.models import PriceBar
from backend.data_quality.validator import DataValidator
from backend.pipeline.exceptions import (
    PipelineConfigurationError,
    PipelineStageError,
    ProviderFetchError,
)
from backend.pipeline.market_pipeline import MarketPipeline
from backend.pipeline.models import (
    PipelineConfig,
    PipelineReport,
    PipelineStatus,
    StageName,
    StageResult,
    SymbolReport,
    SymbolStatus,
)
from backend.pipeline.pipeline_context import PipelineContext
from backend.pipeline.pipeline_executor import PipelineExecutor
from backend.pipeline.pipeline_factory import PipelineFactory
from backend.pipeline.pipeline_report import PipelineReportGenerator
from backend.storage.models import DatasetType, StorageRequest, StorageResult

# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------


def _bar(day: int, close: float = 100.0) -> PriceBar:
    """Create a PriceBar for testing."""
    return PriceBar(
        trade_date=date(2024, 1, day),
        open=close - 0.5,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=1000,
    )


def _bars(n: int = 5, close: float = 100.0) -> tuple[PriceBar, ...]:
    """Create a tuple of PriceBars."""
    return tuple(_bar(i + 1, close) for i in range(n))


def _payload(n: int = 5) -> tuple[dict[str, Any], ...]:
    """Create a payload tuple of dicts."""
    return tuple(
        {
            "date": f"2024-01-{i + 1:02d}",
            "open": 99.5,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000,
        }
        for i in range(n)
    )


def _data_response(
    symbol: str = "RELIANCE",
    exchange: str = "NSE",
    n: int = 5,
    status: DataStatus = DataStatus.SUCCESS,
) -> DataResponse:
    """Create a DataResponse for testing."""
    return DataResponse(
        request=DataRequest(
            symbol=symbol,
            exchange=exchange,
            data_type=DataType.PRICE_DAILY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
        ),
        provider="upstox",
        timestamp=datetime.now().astimezone(),
        status=status,
        payload=_payload(n),
    )


def _storage_result(success: bool = True) -> StorageResult:
    """Create a StorageResult for testing."""
    return StorageResult(
        success=success,
        storage_id="test:storage:1",
        version="test",
        timestamp=datetime.now().astimezone(),
    )


class MockDataEngine:
    """Mock data engine for testing."""

    def __init__(
        self,
        response: DataResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self._response = response or _data_response()
        self._error = error
        self.call_count = 0

    def get_data(self, request: DataRequest) -> DataResponse:
        self.call_count += 1
        if self._error:
            raise self._error
        return self._response


class MockRepository:
    """Mock repository for testing."""

    def __init__(
        self,
        result: StorageResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result or _storage_result()
        self._error = error
        self.stored_requests: list[StorageRequest] = []

    def store(self, request: StorageRequest) -> StorageResult:
        self.stored_requests.append(request)
        if self._error:
            raise self._error
        return self._result

    def retrieve(self, request: Any) -> Any:
        pass

    def delete(self, dataset_type: Any, symbol: str) -> bool:
        return True

    def exists(self, dataset_type: Any, symbol: str) -> bool:
        return False

    def supported_dataset_types(self) -> tuple[DatasetType, ...]:
        return (DatasetType.PRICE_DAILY,)


class MockAdjustmentEngine:
    """Mock adjustment engine for testing."""

    def __init__(self, apply_actions: int = 0) -> None:
        self._apply_actions = apply_actions
        self.call_count = 0

    def adjust_prices(self, request: Any) -> Any:
        self.call_count += 1
        from datetime import datetime as dt

        from backend.corporate_actions.models import AdjustedPrice, AdjustmentResult

        adjusted = []
        for raw in request.raw_prices:
            trade_date = raw.get("date")
            if isinstance(trade_date, str):
                trade_date = dt.fromisoformat(trade_date).date()
            adjusted.append(
                AdjustedPrice(
                    trade_date=trade_date,
                    open=float(raw.get("open", 0)),
                    high=float(raw.get("high", 0)),
                    low=float(raw.get("low", 0)),
                    close=float(raw.get("close", 0)),
                    adjusted_close=float(raw.get("close", 0)),
                    volume=int(raw.get("volume", 0)),
                    raw_open=float(raw.get("open", 0)),
                    raw_high=float(raw.get("high", 0)),
                    raw_low=float(raw.get("low", 0)),
                    raw_close=float(raw.get("close", 0)),
                    raw_volume=int(raw.get("volume", 0)),
                    factor=1.0,
                )
            )

        return AdjustmentResult(
            symbol=request.symbol,
            exchange=request.exchange,
            prices=tuple(adjusted),
            actions_applied=tuple(),
            raw_preserved=True,
            generated_at=dt.now().astimezone(),
        )


# ---------------------------------------------------------------------------
# PipelineConfig tests
# ---------------------------------------------------------------------------


class TestPipelineConfig:
    def test_default_config(self):
        config = PipelineConfig()
        assert config.exchange == "NSE"
        assert config.batch_size == 10
        assert config.skip_validation is False
        assert config.skip_quality is False
        assert config.skip_ca is False

    def test_custom_config(self):
        config = PipelineConfig(
            exchange="BSE",
            batch_size=20,
            skip_validation=True,
        )
        assert config.exchange == "BSE"
        assert config.batch_size == 20
        assert config.skip_validation is True


# ---------------------------------------------------------------------------
# PipelineContext tests
# ---------------------------------------------------------------------------


class TestPipelineContext:
    def test_valid_context(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        assert context.data_engine is not None
        assert context.repository is not None

    def test_missing_data_engine(self):
        with pytest.raises(ValueError, match="data_engine is required"):
            PipelineContext(
                data_engine=None,  # type: ignore
                repository=MockRepository(),
                validator=DataValidator(),
                anomaly_detector=AnomalyDetectorEngine(),
                adjustment_engine=MockAdjustmentEngine(),
            )

    def test_missing_repository(self):
        with pytest.raises(ValueError, match="repository is required"):
            PipelineContext(
                data_engine=MockDataEngine(),
                repository=None,  # type: ignore
                validator=DataValidator(),
                anomaly_detector=AnomalyDetectorEngine(),
                adjustment_engine=MockAdjustmentEngine(),
            )


# ---------------------------------------------------------------------------
# StageResult tests
# ---------------------------------------------------------------------------


class TestStageResult:
    def test_success_result(self):
        result = StageResult(
            stage=StageName.FETCH,
            success=True,
            duration=1.5,
            message="Fetched 100 records",
        )
        assert result.stage == StageName.FETCH
        assert result.success is True
        assert result.duration == 1.5

    def test_failure_result(self):
        result = StageResult(
            stage=StageName.PERSIST,
            success=False,
            message="Database connection failed",
        )
        assert result.success is False
        assert "Database" in result.message


# ---------------------------------------------------------------------------
# SymbolReport tests
# ---------------------------------------------------------------------------


class TestSymbolReport:
    def test_success_report(self):
        report = SymbolReport(
            symbol="RELIANCE",
            exchange="NSE",
            status=SymbolStatus.SUCCESS,
            records_fetched=100,
            records_inserted=100,
        )
        assert report.symbol == "RELIANCE"
        assert report.status == SymbolStatus.SUCCESS
        assert report.records_fetched == 100

    def test_failed_report(self):
        report = SymbolReport(
            symbol="TCS",
            exchange="NSE",
            status=SymbolStatus.FAILED,
            error="Provider timeout",
        )
        assert report.status == SymbolStatus.FAILED
        assert report.error == "Provider timeout"


# ---------------------------------------------------------------------------
# PipelineReport tests
# ---------------------------------------------------------------------------


class TestPipelineReport:
    def test_empty_report(self):
        report = PipelineReport(status=PipelineStatus.SUCCESS)
        assert report.status == PipelineStatus.SUCCESS
        assert report.symbols_processed == 0


# ---------------------------------------------------------------------------
# PipelineReportGenerator tests
# ---------------------------------------------------------------------------


class TestPipelineReportGenerator:
    def test_generate_success(self):
        gen = PipelineReportGenerator()
        started = datetime.now().astimezone()
        completed = started + timedelta(seconds=5)

        symbol_reports = (
            SymbolReport(
                symbol="RELIANCE",
                exchange="NSE",
                status=SymbolStatus.SUCCESS,
                records_fetched=100,
                records_inserted=100,
            ),
            SymbolReport(
                symbol="TCS",
                exchange="NSE",
                status=SymbolStatus.SUCCESS,
                records_fetched=50,
                records_inserted=50,
            ),
        )

        report = gen.generate(symbol_reports, started, completed)
        assert report.status == PipelineStatus.SUCCESS
        assert report.symbols_processed == 2
        assert report.symbols_succeeded == 2
        assert report.symbols_failed == 0
        assert report.records_downloaded == 150
        assert report.records_inserted == 150
        assert report.elapsed_seconds == pytest.approx(5.0)

    def test_generate_partial(self):
        gen = PipelineReportGenerator()
        started = datetime.now().astimezone()
        completed = started + timedelta(seconds=3)

        symbol_reports = (
            SymbolReport(
                symbol="RELIANCE",
                exchange="NSE",
                status=SymbolStatus.SUCCESS,
                records_fetched=100,
                records_inserted=100,
            ),
            SymbolReport(
                symbol="TCS",
                exchange="NSE",
                status=SymbolStatus.FAILED,
                error="Provider timeout",
            ),
        )

        report = gen.generate(symbol_reports, started, completed)
        assert report.status == PipelineStatus.PARTIAL
        assert report.symbols_failed == 1
        assert len(report.failures) == 1
        assert "TCS" in report.failures[0]

    def test_generate_failed(self):
        gen = PipelineReportGenerator()
        started = datetime.now().astimezone()
        completed = started + timedelta(seconds=1)

        symbol_reports = (
            SymbolReport(
                symbol="RELIANCE",
                exchange="NSE",
                status=SymbolStatus.FAILED,
                error="Provider unavailable",
            ),
        )

        report = gen.generate(symbol_reports, started, completed)
        assert report.status == PipelineStatus.FAILED
        assert report.symbols_succeeded == 0


# ---------------------------------------------------------------------------
# PipelineExecutor tests
# ---------------------------------------------------------------------------


class TestPipelineExecutor:
    def test_execute_fetch_success(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        executor = PipelineExecutor(context)

        result = executor.execute_fetch("RELIANCE", "NSE", date(2024, 1, 1), date(2024, 1, 5))
        assert result.success is True
        assert result.stage == StageName.FETCH
        assert "response" in result.metadata

    def test_execute_fetch_failure(self):
        engine = MockDataEngine(error=Exception("Network timeout"))
        context = PipelineContext(
            data_engine=engine,
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        executor = PipelineExecutor(context)

        result = executor.execute_fetch("RELIANCE", "NSE", date(2024, 1, 1), date(2024, 1, 5))
        assert result.success is False
        assert "Network timeout" in result.message

    def test_execute_fetch_failed_status(self):
        engine = MockDataEngine(response=_data_response(status=DataStatus.FAILED))
        context = PipelineContext(
            data_engine=engine,
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        executor = PipelineExecutor(context)

        result = executor.execute_fetch("RELIANCE", "NSE", date(2024, 1, 1), date(2024, 1, 5))
        assert result.success is False
        assert "FAILED status" in result.message

    def test_execute_validate_success(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        executor = PipelineExecutor(context)
        response = _data_response()

        result = executor.execute_validate("RELIANCE", "NSE", response)
        assert result.success is True
        assert result.stage == StageName.VALIDATE

    def test_execute_normalize_success(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        executor = PipelineExecutor(context)
        response = _data_response()
        bars = _bars()

        result = executor.execute_normalize("RELIANCE", response, bars)
        assert result.success is True
        assert result.stage == StageName.NORMALIZE
        assert "records" in result.metadata
        assert len(result.metadata["records"]) == 5

    def test_execute_persist_success(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        executor = PipelineExecutor(context)
        records = tuple({"date": "2024-01-01", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000, "symbol": "RELIANCE", "exchange": "NSE"})

        result = executor.execute_persist("RELIANCE", "NSE", records)
        assert result.success is True
        assert result.stage == StageName.PERSIST

    def test_execute_persist_failure(self):
        repo = MockRepository(error=Exception("Database unavailable"))
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=repo,
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        executor = PipelineExecutor(context)
        records = tuple({"date": "2024-01-01", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000, "symbol": "RELIANCE", "exchange": "NSE"})

        result = executor.execute_persist("RELIANCE", "NSE", records)
        assert result.success is False
        assert "Database unavailable" in result.message

    def test_execute_data_quality_success(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        executor = PipelineExecutor(context)
        bars = _bars()

        result = executor.execute_data_quality("RELIANCE", "NSE", bars)
        assert result.success is True
        assert result.stage == StageName.DATA_QUALITY

    def test_convert_to_bars(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        executor = PipelineExecutor(context)
        payload = _payload(3)

        bars = executor._convert_to_bars(payload)
        assert len(bars) == 3
        assert bars[0].trade_date == date(2024, 1, 1)
        assert bars[0].close == 100.0

    def test_bars_to_records(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        executor = PipelineExecutor(context)
        bars = _bars(3)

        records = executor._bars_to_records(bars, "RELIANCE", "NSE")
        assert len(records) == 3
        assert records[0]["symbol"] == "RELIANCE"
        assert records[0]["exchange"] == "NSE"
        assert records[0]["date"] == "2024-01-01"


# ---------------------------------------------------------------------------
# MarketPipeline tests
# ---------------------------------------------------------------------------


class TestMarketPipeline:
    def test_run_single_symbol(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        pipeline = MarketPipeline(context)

        report = pipeline.run("RELIANCE", "NSE", date(2024, 1, 1), date(2024, 1, 5))
        assert report.status == PipelineStatus.SUCCESS
        assert report.symbols_processed == 1
        assert report.symbols_succeeded == 1
        assert report.records_downloaded == 5

    def test_run_multiple_symbols(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        pipeline = MarketPipeline(context)

        report = pipeline.run_many(
            ("RELIANCE", "TCS", "INFY"),
            "NSE",
            date(2024, 1, 1),
            date(2024, 1, 5),
        )
        assert report.symbols_processed == 3
        assert report.symbols_succeeded == 3
        assert report.records_downloaded == 15

    def test_run_provider_failure_recovery(self):
        engine = MockDataEngine(error=Exception("API timeout"))
        context = PipelineContext(
            data_engine=engine,
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        pipeline = MarketPipeline(context)

        report = pipeline.run_many(
            ("RELIANCE", "TCS"),
            "NSE",
            date(2024, 1, 1),
            date(2024, 1, 5),
        )
        assert report.status == PipelineStatus.FAILED
        assert report.symbols_failed == 2

    def test_run_persistence_failure(self):
        repo = MockRepository(error=Exception("Connection refused"))
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=repo,
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        pipeline = MarketPipeline(context)

        report = pipeline.run("RELIANCE", "NSE", date(2024, 1, 1), date(2024, 1, 5))
        assert report.status == PipelineStatus.FAILED
        assert len(report.failures) == 1
        assert "Connection refused" in report.failures[0]

    def test_run_empty_dataset(self):
        engine = MockDataEngine(response=_data_response(n=0))
        context = PipelineContext(
            data_engine=engine,
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        pipeline = MarketPipeline(context)

        report = pipeline.run("RELIANCE", "NSE", date(2024, 1, 1), date(2024, 1, 5))
        assert report.status == PipelineStatus.SUCCESS
        assert report.records_downloaded == 0

    def test_run_incremental(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        pipeline = MarketPipeline(context)

        report = pipeline.run_incremental(("RELIANCE",), "NSE", days=7)
        assert report.status == PipelineStatus.SUCCESS
        assert report.symbols_processed == 1

    def test_run_full_history(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        pipeline = MarketPipeline(context)

        report = pipeline.run_full_history(("RELIANCE",), "NSE", years=1)
        assert report.status == PipelineStatus.SUCCESS
        assert report.symbols_processed == 1

    def test_skip_validation(self):
        config = PipelineConfig(skip_validation=True)
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
            config=config,
        )
        pipeline = MarketPipeline(context)

        report = pipeline.run("RELIANCE", "NSE", date(2024, 1, 1), date(2024, 1, 5))
        assert report.status == PipelineStatus.SUCCESS

    def test_skip_quality(self):
        config = PipelineConfig(skip_quality=True)
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
            config=config,
        )
        pipeline = MarketPipeline(context)

        report = pipeline.run("RELIANCE", "NSE", date(2024, 1, 1), date(2024, 1, 5))
        assert report.status == PipelineStatus.SUCCESS

    def test_skip_ca(self):
        config = PipelineConfig(skip_ca=True)
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
            config=config,
        )
        pipeline = MarketPipeline(context)

        report = pipeline.run("RELIANCE", "NSE", date(2024, 1, 1), date(2024, 1, 5))
        assert report.status == PipelineStatus.SUCCESS


# ---------------------------------------------------------------------------
# PipelineFactory tests
# ---------------------------------------------------------------------------


class TestPipelineFactory:
    def test_create_default_pipeline(self):
        mock_registry = MagicMock()
        mock_conn_manager = MagicMock()

        pipeline = create_default_pipeline(
            registry=mock_registry,
            conn_manager=mock_conn_manager,
        )
        assert pipeline is not None
        assert pipeline.context is not None
        assert pipeline.context.data_engine is not None
        assert pipeline.context.repository is not None

    def test_create_with_custom_config(self):
        mock_registry = MagicMock()
        mock_conn_manager = MagicMock()
        config = PipelineConfig(exchange="BSE", batch_size=5)

        pipeline = create_default_pipeline(
            registry=mock_registry,
            conn_manager=mock_conn_manager,
            config=config,
        )
        assert pipeline.context.config.exchange == "BSE"
        assert pipeline.context.config.batch_size == 5

    def test_create_with_context(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        pipeline = PipelineFactory.create_with_context(context)
        assert pipeline.context is context


# ---------------------------------------------------------------------------
# Exception tests
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_pipeline_stage_error(self):
        error = PipelineStageError("fetch", "Network timeout", recoverable=True)
        assert error.stage == "fetch"
        assert error.recoverable is True
        assert "Network timeout" in str(error)

    def test_provider_fetch_error(self):
        error = ProviderFetchError("RELIANCE", "API limit exceeded")
        assert error.symbol == "RELIANCE"
        assert error.recoverable is True
        assert "RELIANCE" in str(error)

    def test_pipeline_configuration_error(self):
        error = PipelineConfigurationError("Missing registry")
        assert "Missing registry" in str(error)


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_full_pipeline_flow(self):
        context = PipelineContext(
            data_engine=MockDataEngine(),
            repository=MockRepository(),
            validator=DataValidator(),
            anomaly_detector=AnomalyDetectorEngine(),
            adjustment_engine=MockAdjustmentEngine(),
        )
        pipeline = MarketPipeline(context)

        report = pipeline.run("RELIANCE", "NSE", date(2024, 1, 1), date(2024, 1, 5))

        assert report.status == PipelineStatus.SUCCESS
        assert report.symbols_processed == 1
        assert report.symbols_succeeded == 1
        assert report.records_downloaded == 5
        assert report.records_inserted == 5
        assert report.elapsed_seconds >= 0
        assert report.started_at is not None
        assert report.completed_at is not None
        assert len(report.symbol_reports) == 1

        symbol_report = report.symbol_reports[0]
        assert symbol_report.symbol == "RELIANCE"
        assert symbol_report.status == SymbolStatus.SUCCESS
        assert len(symbol_report.stages) == 6

    def test_report_correctness(self):
        gen = PipelineReportGenerator()
        started = datetime(2024, 1, 1, 10, 0, 0).astimezone()
        completed = datetime(2024, 1, 1, 10, 0, 10).astimezone()

        symbol_reports = (
            SymbolReport(
                symbol="RELIANCE",
                exchange="NSE",
                status=SymbolStatus.SUCCESS,
                records_fetched=100,
                records_inserted=95,
                records_updated=5,
                duplicates=3,
                anomalies=2,
            ),
            SymbolReport(
                symbol="TCS",
                exchange="NSE",
                status=SymbolStatus.SUCCESS,
                records_fetched=50,
                records_inserted=50,
                duplicates=0,
                anomalies=0,
            ),
            SymbolReport(
                symbol="INFY",
                exchange="NSE",
                status=SymbolStatus.FAILED,
                error="Provider error",
            ),
        )

        report = gen.generate(symbol_reports, started, completed)

        assert report.status == PipelineStatus.PARTIAL
        assert report.symbols_processed == 3
        assert report.symbols_succeeded == 2
        assert report.symbols_failed == 1
        assert report.records_downloaded == 150
        assert report.records_inserted == 145
        assert report.records_updated == 5
        assert report.duplicates == 3
        assert report.anomalies == 2
        assert report.elapsed_seconds == 10.0
        assert len(report.failures) == 1
        assert "INFY" in report.failures[0]
