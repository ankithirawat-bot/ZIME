"""
Recommendation Engine.

Aggregates output from the :class:`AnalyticsPipeline` into a single
actionable recommendation.  The only dependency on the analytics domain
is the pipeline itself — individual engines are never referenced.
"""

from __future__ import annotations

from statistics import mean

from backend.analytics.models import AnalyticsContext
from backend.analytics.pipeline import AnalyticsPipeline
from backend.cache.key import make_cache_key
from backend.cache.provider import CacheProvider
from backend.recommendation.models import RecommendationResult

_WEIGHTS: dict[str, float] = {
    "Trend": 0.30,
    "Momentum": 0.20,
    "Volume": 0.15,
    "Relative Strength": 0.20,
    "Volatility": 0.15,
}

_DEFAULT_TTL: float = 300.0


class RecommendationEngine:
    """Produces an actionable recommendation from the analytics pipeline."""

    def __init__(
        self,
        pipeline: AnalyticsPipeline | None = None,
        cache: CacheProvider | None = None,
        ttl: float = _DEFAULT_TTL,
    ) -> None:
        """Initialize the recommendation engine.

        Args:
            pipeline: Analytics pipeline (default created).
            cache:    Optional cache provider.  ``None`` disables caching.
            ttl:      Cache TTL in seconds (default 300).
        """
        self._pipeline = pipeline if pipeline is not None else AnalyticsPipeline()
        self._cache = cache
        self._ttl = ttl

    def analyze(self, context: AnalyticsContext) -> RecommendationResult:
        """Run the analytics pipeline and produce a recommendation.

        Results are cached when a :class:`CacheProvider` is configured.
        The cache is keyed deterministically from the *context*.

        Args:
            context: Normalized market data, corporate actions and config.

        Returns:
            RecommendationResult with recommendation, confidence and facts.
        """
        # --- cache lookup --------------------------------------------------
        cache_key = make_cache_key(context) if self._cache is not None else None
        if cache_key is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # --- pipeline execution --------------------------------------------
        result = self._pipeline.run(context)

        if not result.facts:
            rec_result = RecommendationResult(
                recommendation="Insufficient Data",
                confidence=0.0,
                facts={},
                metadata={"errors": dict(result.errors)},
            )
        else:
            weighted_score = 0.0
            total_weight = 0.0
            confidences: list[float] = []

            for name in result.execution_order:
                fact = result.facts.get(name)
                if fact is None:
                    continue
                weight = _WEIGHTS.get(name, 0.10)
                weighted_score += weight * float(
                    fact.metadata.get("combined_score", 0)
                )
                total_weight += weight
                confidences.append(fact.confidence)

            normalized = (
                (weighted_score / total_weight) if total_weight > 0 else 0.0
            )
            avg_confidence = mean(confidences) if confidences else 0.0

            recommendation = self._classify(normalized)

            rec_result = RecommendationResult(
                recommendation=recommendation,
                confidence=round(avg_confidence, 2),
                facts=dict(result.facts),
                metadata={
                    "weighted_score": round(normalized, 4),
                    "available_facts": len(result.facts),
                    "total_engines": len(result.execution_order),
                    "failed_engines": dict(result.errors),
                    "pipeline_duration": round(result.total_duration, 4),
                },
            )

        # --- cache store ---------------------------------------------------
        if cache_key is not None:
            self._cache.set(cache_key, rec_result, ttl=self._ttl)

        return rec_result

    @staticmethod
    def _classify(score: float) -> str:
        """Map a normalised weighted score to a recommendation string."""
        if score >= 0.70:
            return "Strong Buy"
        if score >= 0.45:
            return "Buy"
        if score >= 0.20:
            return "Monitor"
        if score >= -0.10:
            return "Watchlist"
        return "Avoid"
