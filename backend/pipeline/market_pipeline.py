"""Market data pipeline orchestrator.

Integrates Upstox Provider, Data Validation, Data Quality, Corporate Actions,
PostgreSQL Storage, and Orchestration into a production pipeline.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from backend.pipeline.exceptions import (
    PipelineStageError,
)
from backend.pipeline.models import (
    PipelineReport,
    StageResult,
    SymbolReport,
    SymbolStatus,
)
from backend.pipeline.pipeline_context import PipelineContext
from backend.pipeline.pipeline_executor import PipelineExecutor
from backend.pipeline.pipeline_report import PipelineReportGenerator


class MarketPipeline:
    """Production pipeline for market data processing.

    Integrates all data platform components into a cohesive pipeline
    with proper error handling and recovery.

    Attributes:
        context:  Pipeline context with all dependencies.
        executor: Stage executor.
        report_gen: Report generator.
    """

    def __init__(self, context: PipelineContext) -> None:
        self._context = context
        self._executor = PipelineExecutor(context)
        self._report_gen = PipelineReportGenerator()
        self._logger = context.logger

    @property
    def context(self) -> PipelineContext:
        """Access the pipeline context."""
        return self._context

    def run(
        self,
        symbol: str,
        exchange: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> PipelineReport:
        """Process a single symbol through the full pipeline.

        Args:
            symbol:      Ticker symbol to process.
            exchange:    Exchange identifier (defaults to config).
            start_date:  Start date (defaults to config).
            end_date:    End date (defaults to config).

        Returns:
            PipelineReport with processing results.
        """
        return self.run_many(
            (symbol,),
            exchange=exchange,
            start_date=start_date,
            end_date=end_date,
        )

    def run_many(
        self,
        symbols: tuple[str, ...],
        exchange: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> PipelineReport:
        """Process multiple symbols through the full pipeline.

        Recoverable failures do not stop processing of remaining symbols.

        Args:
            symbols:     Tuple of ticker symbols to process.
            exchange:    Exchange identifier (defaults to config).
            start_date:  Start date (defaults to config).
            end_date:    End date (defaults to config).

        Returns:
            PipelineReport with aggregated results.
        """
        started_at = datetime.now().astimezone()
        config = self._context.config

        exchange = exchange or config.exchange
        start_date = start_date or config.start_date or (date.today() - timedelta(days=365))
        end_date = end_date or config.end_date or date.today()

        symbol_reports: list[SymbolReport] = []

        for symbol in symbols:
            try:
                report = self._process_symbol(symbol, exchange, start_date, end_date)
                symbol_reports.append(report)
            except PipelineStageError as e:
                if not e.recoverable:
                    raise
                self._logger.error("Recoverable error processing %s: %s", symbol, e)
                symbol_reports.append(
                    SymbolReport(
                        symbol=symbol,
                        exchange=exchange,
                        status=SymbolStatus.FAILED,
                        error=str(e),
                        started_at=started_at,
                        completed_at=datetime.now().astimezone(),
                    )
                )
            except Exception as e:
                self._logger.error("Unexpected error processing %s: %s", symbol, e)
                symbol_reports.append(
                    SymbolReport(
                        symbol=symbol,
                        exchange=exchange,
                        status=SymbolStatus.FAILED,
                        error=f"Unexpected error: {e}",
                        started_at=started_at,
                        completed_at=datetime.now().astimezone(),
                    )
                )

        completed_at = datetime.now().astimezone()
        return self._report_gen.generate(
            tuple(symbol_reports), started_at, completed_at
        )

    def run_incremental(
        self,
        symbols: tuple[str, ...] | None = None,
        exchange: str | None = None,
        days: int = 7,
    ) -> PipelineReport:
        """Run incremental update for specified or all symbols.

        Fetches data for the last N days.

        Args:
            symbols:  Symbols to update (None for all known symbols).
            exchange: Exchange identifier (defaults to config).
            days:     Number of days to fetch.

        Returns:
            PipelineReport with processing results.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        return self.run_many(
            symbols or (),
            exchange=exchange,
            start_date=start_date,
            end_date=end_date,
        )

    def run_full_history(
        self,
        symbols: tuple[str, ...] | None = None,
        exchange: str | None = None,
        years: int = 5,
    ) -> PipelineReport:
        """Run full history download for specified or all symbols.

        Fetches data for the specified number of years.

        Args:
            symbols:  Symbols to update (None for all known symbols).
            exchange: Exchange identifier (defaults to config).
            years:    Number of years of history to fetch.

        Returns:
            PipelineReport with processing results.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=years * 365)

        return self.run_many(
            symbols or (),
            exchange=exchange,
            start_date=start_date,
            end_date=end_date,
        )

    def _process_symbol(
        self,
        symbol: str,
        exchange: str,
        start_date: date,
        end_date: date,
    ) -> SymbolReport:
        """Process a single symbol through all pipeline stages.

        Args:
            symbol:      Ticker symbol.
            exchange:    Exchange identifier.
            start_date:  Start date for data request.
            end_date:    End date for data request.

        Returns:
            SymbolReport with processing results.

        Raises:
            ProviderFetchError: If fetch fails and is not recoverable.
        """
        started_at = datetime.now().astimezone()
        stages: list[StageResult] = []
        records_fetched = 0
        records_inserted = 0
        duplicates = 0
        anomalies = 0

        # Stage 1: Fetch
        fetch_result = self._executor.execute_fetch(symbol, exchange, start_date, end_date)
        stages.append(fetch_result)

        if not fetch_result.success:
            return SymbolReport(
                symbol=symbol,
                exchange=exchange,
                status=SymbolStatus.FAILED,
                stages=tuple(stages),
                error=fetch_result.message,
                started_at=started_at,
                completed_at=datetime.now().astimezone(),
            )

        response = fetch_result.metadata.get("response")
        records_fetched = len(response.payload) if response else 0

        # Stage 2: Validate (unless skipped)
        if not self._context.config.skip_validation:
            validate_result = self._executor.execute_validate(symbol, exchange, response)
            stages.append(validate_result)

            if not validate_result.success:
                return SymbolReport(
                    symbol=symbol,
                    exchange=exchange,
                    status=SymbolStatus.FAILED,
                    records_fetched=records_fetched,
                    stages=tuple(stages),
                    error=validate_result.message,
                    started_at=started_at,
                    completed_at=datetime.now().astimezone(),
                )

            bars = validate_result.metadata.get("bars", ())
        else:
            bars = self._executor._convert_to_bars(response.payload)

        # Stage 3: Normalize
        normalize_result = self._executor.execute_normalize(symbol, response, bars)
        stages.append(normalize_result)

        if not normalize_result.success:
            return SymbolReport(
                symbol=symbol,
                exchange=exchange,
                status=SymbolStatus.FAILED,
                records_fetched=records_fetched,
                stages=tuple(stages),
                error=normalize_result.message,
                started_at=started_at,
                completed_at=datetime.now().astimezone(),
            )

        records = normalize_result.metadata.get("records", ())

        # Stage 4: Corporate Action (unless skipped)
        if not self._context.config.skip_ca:
            ca_result = self._executor.execute_corporate_action(symbol, exchange, records)
            stages.append(ca_result)

            if ca_result.success:
                records = ca_result.metadata.get("records", records)

        # Stage 5: Data Quality (unless skipped)
        if not self._context.config.skip_quality:
            quality_result = self._executor.execute_data_quality(symbol, exchange, bars)
            stages.append(quality_result)
            anomalies = quality_result.metadata.get("anomalies", 0)

        # Stage 6: Persist
        persist_result = self._executor.execute_persist(symbol, exchange, records)
        stages.append(persist_result)

        if not persist_result.success:
            return SymbolReport(
                symbol=symbol,
                exchange=exchange,
                status=SymbolStatus.FAILED,
                records_fetched=records_fetched,
                stages=tuple(stages),
                error=persist_result.message,
                started_at=started_at,
                completed_at=datetime.now().astimezone(),
            )

        records_inserted = persist_result.metadata.get("inserted", 0)

        return SymbolReport(
            symbol=symbol,
            exchange=exchange,
            status=SymbolStatus.SUCCESS,
            records_fetched=records_fetched,
            records_inserted=records_inserted,
            duplicates=duplicates,
            anomalies=anomalies,
            stages=tuple(stages),
            started_at=started_at,
            completed_at=datetime.now().astimezone(),
        )
