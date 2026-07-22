"""Shared analytics engine orchestration.

Encapsulates the common evaluation pipeline used by all analytics engines
so that domain-specific engines only provide their own signal registry,
evaluator and scorer implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.analytics.models import AnalyticsContext, AnalyticsFact


class AnalyticsEngineBase(ABC):
    """Abstract base encapsulating the common analytics evaluation pipeline.

    Subclasses must provide constructor arguments (registry, evaluator, scorer)
    and implement :meth:`_engine_name`.  The :meth:`analyze` method executes
    the shared workflow:

    1. Optional pre-condition check (override :meth:`_check_preconditions`).
    2. Run all registered signals against the context.
    3. Evaluate combined signal outputs.
    4. Compute scoring from the evaluated result.
    5. Gather warnings.
    6. Return an immutable :class:`AnalyticsFact`.
    """

    def __init__(
        self,
        registry: Any,
        evaluator: Any,
        scorer: Any,
    ) -> None:
        self._registry = registry
        self._evaluator = evaluator
        self._scorer = scorer

    # ---- overridable hooks ------------------------------------------------

    @abstractmethod
    def _engine_name(self) -> str:
        """Return the fact name for this engine (e.g. ``"Trend"``)."""
        ...

    def _check_preconditions(self, context: AnalyticsContext) -> None:
        """Optional pre-condition check; override to validate *context*."""
        return None

    # ---- shared public method ---------------------------------------------

    def analyze(self, context: AnalyticsContext) -> AnalyticsFact:
        """Execute the common evaluation pipeline.

        Args:
            context: Normalized market data, corporate actions and config.

        Returns:
            AnalyticsFact with engine-specific state, confidence and evidence.
        """
        self._check_preconditions(context)

        outputs: list[Any] = [
            signal(context) for signal in self._registry.all().values()
        ]
        result = self._evaluator.evaluate(outputs, context.config)

        completeness = (
            result.available_count / result.total_count if result.total_count else 0.0
        )
        scoring = self._scorer.score(result, completeness)
        warnings = self._warnings(context, outputs, result)

        metadata: dict[str, Any] = {
            "combined_score": round(result.combined_score, 4),
            "agreement": round(result.agreement, 4),
            "completeness": round(completeness, 4),
            "conflict": result.conflict,
            "signal_scores": {o.name: round(o.score, 4) for o in outputs},
            "available_signals": result.available_count,
            "bars_analyzed": len(context.prices),
            "warnings": warnings,
        }

        return AnalyticsFact(
            name=self._engine_name(),
            state=scoring.state.value,
            confidence=scoring.confidence,
            evidence=tuple(e.text for e in scoring.evidence),
            metadata=metadata,
        )

    # ---- shared helpers ---------------------------------------------------

    @staticmethod
    def _warnings(
        context: AnalyticsContext,
        outputs: list[Any],
        result: Any,
    ) -> list[str]:
        """Collect human-readable warnings about data / signal quality."""
        warnings: list[str] = []
        if not context.prices:
            warnings.append("No price data available")
        for output in outputs:
            if not output.available:
                warnings.append(f"Signal '{output.name}' lacked sufficient data")
        if result.conflict:
            warnings.append("Conflicting signals observed")
        if 0 < result.available_count < result.total_count:
            warnings.append("Some signals lacked sufficient data")
        return warnings
