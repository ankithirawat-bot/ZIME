"""Regime scoring and transition analysis.

Computes regime scores, transition probabilities, and
adaptive recommendations for downstream engines.
"""

from __future__ import annotations

from backend.regime.models import (
    RegimeFeatures,
    RegimeResult,
    RegimeScore,
    RegimeStatistics,
    RegimeType,
)

_RECOMMENDATIONS: dict[RegimeType, dict[str, str]] = {
    RegimeType.TRENDING_BULL: {
        "strategy": "Increase trend-following weight",
        "sizing": "Standard position sizing",
        "portfolio": "Full equity allocation",
        "risk": "Normal risk limits",
        "volatility": "Prefer GARCH forecast",
        "backtesting": "Use bull market regime",
    },
    RegimeType.TRENDING_BEAR: {
        "strategy": "Increase defensive positions",
        "sizing": "Reduce position sizes by 25%",
        "portfolio": "Increase cash allocation",
        "risk": "Tighten VaR limits",
        "volatility": "Prefer EGARCH forecast",
        "backtesting": "Use bear market regime",
    },
    RegimeType.SIDEWAYS: {
        "strategy": "Reduce breakout signals",
        "sizing": "Reduce position sizes by 15%",
        "portfolio": "Balanced allocation",
        "risk": "Reduce max drawdown limit",
        "volatility": "Prefer EWMA forecast",
        "backtesting": "Use range-bound regime",
    },
    RegimeType.ACCUMULATION: {
        "strategy": "Gradually increase exposure",
        "sizing": "Scale into positions gradually",
        "portfolio": "Increase equity allocation",
        "risk": "Standard risk limits",
        "volatility": "Prefer GARCH forecast",
        "backtesting": "Use accumulation regime",
    },
    RegimeType.DISTRIBUTION: {
        "strategy": "Reduce exposure gradually",
        "sizing": "Reduce position sizes by 20%",
        "portfolio": "Increase cash position",
        "risk": "Tighten concentration limits",
        "volatility": "Prefer EGARCH forecast",
        "backtesting": "Use distribution regime",
    },
    RegimeType.RECOVERY: {
        "strategy": "Increase cyclical exposure",
        "sizing": "Standard position sizing",
        "portfolio": "Gradually increase equity",
        "risk": "Moderate risk limits",
        "volatility": "Prefer GARCH forecast",
        "backtesting": "Use recovery regime",
    },
    RegimeType.HIGH_VOLATILITY: {
        "strategy": "Reduce Kelly to 50%",
        "sizing": "Reduce position sizes by 30%",
        "portfolio": "Reduce portfolio beta",
        "risk": "Tighten all risk limits",
        "volatility": "Prefer EGARCH forecast",
        "backtesting": "Use high vol regime",
    },
    RegimeType.LOW_VOLATILITY: {
        "strategy": "Increase position sizing",
        "sizing": "Increase position sizes by 20%",
        "portfolio": "Full equity allocation",
        "risk": "Loosen risk limits",
        "volatility": "Prefer EWMA forecast",
        "backtesting": "Use low vol regime",
    },
    RegimeType.PANIC: {
        "strategy": "Preserve capital",
        "sizing": "Reduce position sizes by 50%",
        "portfolio": "High cash allocation",
        "risk": "Tighten portfolio risk limits",
        "volatility": "Prefer GJR-GARCH forecast",
        "backtesting": "Use panic regime",
    },
    RegimeType.EUPHORIA: {
        "strategy": "Take profits gradually",
        "sizing": "Reduce position sizes by 20%",
        "portfolio": "Reduce equity allocation",
        "risk": "Tighten concentration limits",
        "volatility": "Prefer EGARCH forecast",
        "backtesting": "Use euphoria regime",
    },
    RegimeType.UNKNOWN: {
        "strategy": "Maintain current positions",
        "sizing": "Reduce position sizes by 10%",
        "portfolio": "Neutral allocation",
        "risk": "Standard risk limits",
        "volatility": "Prefer GARCH forecast",
        "backtesting": "Use default regime",
    },
}


def get_recommendations(regime: RegimeType) -> dict[str, str]:
    """Get adaptive recommendations for a regime.

    Args:
        regime: Detected regime type.

    Returns:
        Dict of engine -> recommendation text.
    """
    return _RECOMMENDATIONS.get(regime, _RECOMMENDATIONS[RegimeType.UNKNOWN])


def compute_transition_probability(
    current: RegimeType,
    previous: RegimeType | None,
    features: RegimeFeatures,
    score: RegimeScore,
) -> float:
    """Compute probability of regime transition.

    Args:
        current:  Current detected regime.
        previous: Previous regime (None if first detection).
        features: Current features.
        score:    Current score.

    Returns:
        Transition probability (0 to 1).
    """
    if previous is None or current == previous:
        return max(0.0, 1.0 - score.confidence)
    if score.confidence > 0.8:
        return 0.3 + 0.5 * score.confidence
    if abs(features.trend_strength) > 0.5 or features.volatility_change > 0.3:
        return 0.4 + 0.3 * max(abs(features.trend_strength), features.volatility_change)
    return 0.1 + 0.2 * (1 - score.confidence)


def compute_regime_statistics(
    results: tuple[RegimeResult, ...],
) -> RegimeStatistics:
    """Compute statistics from detection history.

    Args:
        results: Historical detection results.

    Returns:
        RegimeStatistics with computed metrics.
    """
    if not results:
        return RegimeStatistics()

    regime_counts: dict[str, int] = {}
    regime_first_seen: dict[str, int] = {}
    transitions = 0

    for i, result in enumerate(results):
        r = result.regime.value
        regime_counts[r] = regime_counts.get(r, 0) + 1
        if r not in regime_first_seen:
            regime_first_seen[r] = i
        if i > 0 and results[i - 1].regime != result.regime:
            transitions += 1

    most_common = max(regime_counts, key=regime_counts.get)

    regime_durations: dict[str, float] = {}
    for r, count in regime_counts.items():
        regime_durations[r] = count / max(len(results), 1)

    stability = 1.0 - (transitions / max(len(results) - 1, 1))

    return RegimeStatistics(
        total_detections=len(results),
        regime_counts=regime_counts,
        regime_durations=regime_durations,
        transition_count=transitions,
        most_common=most_common,
        regime_stability=stability,
    )


def build_transition_matrix(
    results: tuple[RegimeResult, ...],
) -> dict[str, dict[str, float]]:
    """Build regime transition matrix from history.

    Args:
        results: Historical detection results.

    Returns:
        Transition matrix: source -> target -> probability.
    """
    transitions: dict[str, dict[str, int]] = {}
    from_counts: dict[str, int] = {}

    for i in range(1, len(results)):
        prev = results[i - 1].regime.value
        curr = results[i].regime.value
        if prev not in transitions:
            transitions[prev] = {}
        transitions[prev][curr] = transitions[prev].get(curr, 0) + 1
        from_counts[prev] = from_counts.get(prev, 0) + 1

    matrix: dict[str, dict[str, float]] = {}
    for from_regime, targets in transitions.items():
        total = from_counts.get(from_regime, 1)
        matrix[from_regime] = {
            to: count / total for to, count in targets.items()
        }

    return matrix
