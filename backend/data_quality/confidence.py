"""
Confidence engine.

Combines validation outcome, cross-provider agreement and provider
reliability into a single 0-100 :class:`ConfidenceScore` using transparent,
weighted components.
"""

from __future__ import annotations

from backend.data_quality.models import (
    ConfidenceScore,
    ProviderComparison,
    ValidationResult,
)

_SEVERITY_PENALTY = {"high": 25.0, "medium": 10.0, "low": 3.0}


class ConfidenceEngine:
    """Computes a confidence score for a validated data set."""

    def __init__(
        self,
        validation_weight: float = 0.5,
        comparison_weight: float = 0.3,
        reliability_weight: float = 0.2,
    ) -> None:
        total = validation_weight + comparison_weight + reliability_weight
        if total <= 0:
            raise ValueError("weights must sum to a positive value")
        self._w_validation = validation_weight / total
        self._w_comparison = comparison_weight / total
        self._w_reliability = reliability_weight / total

    def compute(
        self,
        symbol: str,
        exchange: str,
        provider: str,
        validation: ValidationResult,
        comparison: ProviderComparison | None = None,
        provider_reliability: float = 1.0,
        historical_reliability: float = 1.0,
    ) -> ConfidenceScore:
        """Compute the confidence score.

        Args:
            symbol:                Instrument symbol.
            exchange:              Exchange identifier.
            provider:              Provider name.
            validation:            Validation result for the provider.
            comparison:            Optional multi-provider comparison.
            provider_reliability:  Provider tier reliability in [0, 1].
            historical_reliability: Historical reliability in [0, 1].

        Returns:
            ConfidenceScore with component breakdown and reasons.
        """
        reasons: list[str] = []

        penalty = 0.0
        for issue in validation.issues:
            penalty += _SEVERITY_PENALTY.get(issue.severity, 5.0)
        validation_component = max(0.0, 100.0 - penalty)
        if validation.issues:
            reasons.append(f"{len(validation.issues)} validation issue(s) reduced confidence")
        else:
            reasons.append("No validation issues")

        if comparison is not None and len(comparison.providers) >= 2:
            comparison_component = comparison.agreement_score
            reasons.append(f"Provider agreement {comparison.agreement_score:.0f}/100")
        else:
            comparison_component = 100.0
            reasons.append("Single provider: no cross-check available")

        reliability_component = (
            (provider_reliability * 0.5 + historical_reliability * 0.5) * 100.0
        )
        reasons.append(f"Reliability component {reliability_component:.0f}/100")

        score = (
            self._w_validation * validation_component
            + self._w_comparison * comparison_component
            + self._w_reliability * reliability_component
        )
        score = max(0.0, min(100.0, score))

        components = {
            "validation": validation_component,
            "comparison": comparison_component,
            "reliability": reliability_component,
        }
        return ConfidenceScore(
            symbol=symbol,
            exchange=exchange,
            provider=provider,
            score=round(score, 2),
            components=components,
            reasons=tuple(reasons),
        )
