"""
Report generator.

Assembles an immutable :class:`ValidationReport` from a request, its
validation result, detected anomalies, confidence score and (optionally) a
provider comparison. Includes a structured summary, flat issue list and
actionable recommendations.
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.data_quality.models import (
    Anomaly,
    ConfidenceScore,
    ProviderComparison,
    ValidationReport,
    ValidationRequest,
    ValidationResult,
)


class ReportGenerator:
    """Builds immutable validation reports from quality components."""

    def generate(
        self,
        request: ValidationRequest,
        validation: ValidationResult,
        confidence: ConfidenceScore,
        anomalies: tuple[Anomaly, ...] = (),
        comparison: ProviderComparison | None = None,
    ) -> ValidationReport:
        """Generate a report.

        Args:
            request:     Original validation request.
            validation:  Validation result.
            confidence:  Confidence score.
            anomalies:   Detected anomalies (default empty).
            comparison:  Optional provider comparison.

        Returns:
            Immutable ValidationReport.
        """
        issues = [issue.message for issue in validation.issues]
        issues.extend(anomaly.description for anomaly in anomalies)

        summary = self._summary(request, validation, confidence, anomalies, comparison)
        recommendations = self._recommendations(validation, anomalies, comparison)

        return ValidationReport(
            request_id=request.request_id,
            symbol=request.symbol,
            exchange=request.exchange,
            provider=request.provider,
            generated_at=datetime.now(UTC),
            summary=summary,
            issues=tuple(issues),
            anomalies=tuple(anomalies),
            confidence=confidence,
            recommendations=tuple(recommendations),
        )

    def _summary(
        self,
        request: ValidationRequest,
        validation: ValidationResult,
        confidence: ConfidenceScore,
        anomalies: tuple[Anomaly, ...],
        comparison: ProviderComparison | None,
    ) -> dict[str, object]:
        summary: dict[str, object] = {
            "symbol": request.symbol,
            "exchange": request.exchange,
            "provider": request.provider,
            "bars": len(request.bars),
            "missing_days": len(validation.missing_days),
            "duplicate_rows": len(validation.duplicate_rows),
            "invalid_ohlc": len(validation.invalid_ohlc),
            "invalid_volume": len(validation.invalid_volume),
            "timestamp_issues": len(validation.timestamp_issues),
            "future_dates": len(validation.future_dates),
            "anomalies": len(anomalies),
            "confidence": confidence.score,
            "is_valid": validation.is_valid,
        }
        if comparison is not None:
            summary["providers"] = list(comparison.providers)
            summary["agreement_score"] = comparison.agreement_score
            summary["corporate_action_divergences"] = len(
                comparison.corporate_action_divergence
            )
        return summary

    def _recommendations(
        self,
        validation: ValidationResult,
        anomalies: tuple[Anomaly, ...],
        comparison: ProviderComparison | None,
    ) -> list[str]:
        recs: list[str] = []
        if validation.missing_days:
            recs.append(f"Backfill {len(validation.missing_days)} missing trading day(s).")
        if validation.duplicate_rows:
            recs.append(f"Remove {len(validation.duplicate_rows)} duplicate bar(s).")
        if validation.invalid_ohlc:
            recs.append(f"Fix {len(validation.invalid_ohlc)} invalid OHLC bar(s).")
        if validation.invalid_volume:
            recs.append(f"Correct {len(validation.invalid_volume)} invalid volume bar(s).")
        if validation.timestamp_issues:
            recs.append(f"Repair {len(validation.timestamp_issues)} out-of-order timestamp(s).")
        if validation.future_dates:
            recs.append(f"Drop {len(validation.future_dates)} future-dated bar(s).")

        by_type: dict[str, int] = {}
        for anomaly in anomalies:
            by_type[anomaly.anomaly_type] = by_type.get(anomaly.anomaly_type, 0) + 1
        for anomaly_type, count in sorted(by_type.items()):
            recs.append(f"Investigate {count} '{anomaly_type}' anomaly(s).")

        if comparison is not None and comparison.corporate_action_divergence:
            recs.append("Reconcile suspected corporate-action divergence between providers.")

        if not recs:
            recs.append("Data passes all quality checks.")
        return recs
