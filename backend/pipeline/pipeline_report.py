"""Pipeline report generation.

Assembles individual symbol reports into an aggregate pipeline report.
"""

from __future__ import annotations

from datetime import datetime

from backend.pipeline.models import (
    PipelineReport,
    PipelineStatus,
    SymbolReport,
    SymbolStatus,
)


class PipelineReportGenerator:
    """Generates aggregate pipeline reports from symbol reports.

    Collects individual symbol processing results and produces
    a unified report with aggregated metrics.
    """

    def generate(
        self,
        symbol_reports: tuple[SymbolReport, ...],
        started_at: datetime,
        completed_at: datetime,
    ) -> PipelineReport:
        """Generate an aggregate pipeline report.

        Args:
            symbol_reports: Individual symbol processing results.
            started_at:     Pipeline start time.
            completed_at:   Pipeline end time.

        Returns:
            PipelineReport with aggregated metrics.
        """
        elapsed = (completed_at - started_at).total_seconds()

        succeeded = sum(
            1 for r in symbol_reports if r.status is SymbolStatus.SUCCESS
        )
        failed = sum(
            1 for r in symbol_reports if r.status is SymbolStatus.FAILED
        )

        records_downloaded = sum(r.records_fetched for r in symbol_reports)
        records_inserted = sum(r.records_inserted for r in symbol_reports)
        records_updated = sum(r.records_updated for r in symbol_reports)
        duplicates = sum(r.duplicates for r in symbol_reports)
        anomalies = sum(r.anomalies for r in symbol_reports)

        warnings: list[str] = []
        failures: list[str] = []
        for report in symbol_reports:
            if report.error:
                failures.append(f"{report.symbol}: {report.error}")
            for stage in report.stages:
                if not stage.success and stage.message:
                    if stage.stage.value in ("fetch", "validate", "normalize"):
                        warnings.append(f"{report.symbol}/{stage.stage}: {stage.message}")

        if failed == 0:
            status = PipelineStatus.SUCCESS
        elif succeeded == 0:
            status = PipelineStatus.FAILED
        else:
            status = PipelineStatus.PARTIAL

        return PipelineReport(
            status=status,
            symbols_processed=len(symbol_reports),
            symbols_succeeded=succeeded,
            symbols_failed=failed,
            records_downloaded=records_downloaded,
            records_inserted=records_inserted,
            records_updated=records_updated,
            duplicates=duplicates,
            anomalies=anomalies,
            warnings=tuple(warnings),
            failures=tuple(failures),
            started_at=started_at,
            completed_at=completed_at,
            elapsed_seconds=elapsed,
            symbol_reports=symbol_reports,
        )
