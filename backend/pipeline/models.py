"""Pipeline models.

Frozen dataclasses for pipeline configuration, execution results,
and report generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class PipelineStatus(StrEnum):
    """Overall pipeline execution status."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class SymbolStatus(StrEnum):
    """Per-symbol processing status."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageName(StrEnum):
    """Pipeline stage identifiers."""

    FETCH = "fetch"
    VALIDATE = "validate"
    NORMALIZE = "normalize"
    CORPORATE_ACTION = "corporate_action"
    DATA_QUALITY = "data_quality"
    PERSIST = "persist"
    REPORT = "report"


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for pipeline execution.

    Attributes:
        exchange:         Default exchange for symbols.
        start_date:       Default start date for data requests.
        end_date:         Default end date for data requests.
        batch_size:       Number of symbols to process in parallel.
        skip_validation:  Skip data validation stage.
        skip_quality:     Skip data quality stage.
        skip_ca:          Skip corporate action adjustment.
    """

    exchange: str = "NSE"
    start_date: date | None = None
    end_date: date | None = None
    batch_size: int = 10
    skip_validation: bool = False
    skip_quality: bool = False
    skip_ca: bool = False


@dataclass(frozen=True)
class StageResult:
    """Result of a single pipeline stage execution.

    Attributes:
        stage:    Stage name.
        success:  Whether the stage completed successfully.
        duration: Time taken in seconds.
        message:  Optional status message.
        metadata: Stage-specific metadata.
    """

    stage: StageName
    success: bool
    duration: float = 0.0
    message: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SymbolReport:
    """Report for a single symbol's processing.

    Attributes:
        symbol:           Ticker symbol.
        exchange:         Exchange identifier.
        status:           Processing outcome.
        records_fetched:  Number of records downloaded.
        records_inserted: Number of records inserted.
        records_updated:  Number of records updated.
        duplicates:       Number of duplicate records skipped.
        anomalies:        Number of anomalies detected.
        stages:           Individual stage results.
        error:            Error message if failed.
        started_at:       Processing start time.
        completed_at:     Processing end time.
    """

    symbol: str
    exchange: str
    status: SymbolStatus
    records_fetched: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    duplicates: int = 0
    anomalies: int = 0
    stages: tuple[StageResult, ...] = field(default_factory=tuple)
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class PipelineReport:
    """Aggregate report for a pipeline run.

    Attributes:
        status:            Overall pipeline status.
        symbols_processed: Number of symbols attempted.
        symbols_succeeded: Number of symbols that completed.
        symbols_failed:    Number of symbols that failed.
        records_downloaded: Total records downloaded.
        records_inserted:  Total records inserted.
        records_updated:   Total records updated.
        duplicates:        Total duplicate records skipped.
        anomalies:         Total anomalies detected.
        warnings:          Non-fatal warnings.
        failures:          Fatal failure messages.
        started_at:        Pipeline start time.
        completed_at:      Pipeline end time.
        elapsed_seconds:   Total elapsed time in seconds.
        symbol_reports:    Per-symbol reports.
    """

    status: PipelineStatus
    symbols_processed: int = 0
    symbols_succeeded: int = 0
    symbols_failed: int = 0
    records_downloaded: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    duplicates: int = 0
    anomalies: int = 0
    warnings: tuple[str, ...] = field(default_factory=tuple)
    failures: tuple[str, ...] = field(default_factory=tuple)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    elapsed_seconds: float = 0.0
    symbol_reports: tuple[SymbolReport, ...] = field(default_factory=tuple)
