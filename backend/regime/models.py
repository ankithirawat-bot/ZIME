"""Market regime detection models.

Frozen dataclasses for regime definitions, features, scores,
results, transitions, and detector protocols.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable


class RegimeType(StrEnum):
    """Market regime types."""

    TRENDING_BULL = "TRENDING_BULL"
    TRENDING_BEAR = "TRENDING_BEAR"
    SIDEWAYS = "SIDEWAYS"
    ACCUMULATION = "ACCUMULATION"
    DISTRIBUTION = "DISTRIBUTION"
    RECOVERY = "RECOVERY"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    PANIC = "PANIC"
    EUPHORIA = "EUPHORIA"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RegimeMetadata:
    """Metadata for a regime definition.

    Attributes:
        name:        Name.
        description: Description.
        version:     Schema version.
        author:      Author.
        created_at:  Creation timestamp.
        tags:        Searchable tags.
    """

    name: str
    description: str = ""
    version: str = "1.0"
    author: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RegimeConfig:
    """Configuration for regime detection.

    Attributes:
        detector:           Default detector name.
        lookback:           Lookback window for features.
        short_lookback:     Short-term lookback.
        volatility_lookback: Volatility lookback.
        trend_lookback:     Trend strength lookback.
        momentum_lookback:  Momentum lookback.
        confidence_threshold: Minimum confidence to confirm.
        transition_min_hold: Min periods before regime change.
        correlation_lookback: Correlation lookback.
        breadth_lookback:   Market breadth lookback.
        min_periods:        Minimum observations required.
        annual_factor:      Annualization factor.
    """

    detector: str = "voting"
    lookback: int = 252
    short_lookback: int = 20
    volatility_lookback: int = 20
    trend_lookback: int = 60
    momentum_lookback: int = 20
    confidence_threshold: float = 0.60
    transition_min_hold: int = 5
    correlation_lookback: int = 60
    breadth_lookback: int = 20
    min_periods: int = 20
    annual_factor: float = 252.0


@dataclass(frozen=True)
class RegimeFeatures:
    """Extracted market features for regime detection.

    Attributes:
        trend_strength:     Trend strength score (-1 to 1).
        momentum:           Momentum score (-1 to 1).
        volatility_level:   Volatility level (0 to 1).
        volatility_change:  Volatility change (-1 to 1).
        breadth:            Market breadth (0 to 1).
        volume_expansion:   Volume expansion score (-1 to 1).
        market_correlation: Average cross-correlation (0 to 1).
        dispersion:         Cross-sectional dispersion (0 to 1).
        drawdown:           Current drawdown (0 to 1).
        recovery_strength:  Recovery strength (0 to 1).
        liquidity_score:    Liquidity score (0 to 1).
    """

    trend_strength: float = 0.0
    momentum: float = 0.0
    volatility_level: float = 0.0
    volatility_change: float = 0.0
    breadth: float = 0.0
    volume_expansion: float = 0.0
    market_correlation: float = 0.0
    dispersion: float = 0.0
    drawdown: float = 0.0
    recovery_strength: float = 0.0
    liquidity_score: float = 0.0


@dataclass(frozen=True)
class RegimeScore:
    """Regime detection scoring information.

    Attributes:
        regime:             Detected regime.
        confidence:         Detection confidence (0 to 1).
        evidence:           Supporting evidence details.
        competing_regimes:  Alternative regimes with scores.
        transition_probability: Estimated transition probability.
    """

    regime: RegimeType = RegimeType.UNKNOWN
    confidence: float = 0.0
    evidence: dict[str, float] = field(default_factory=dict)
    competing_regimes: dict[str, float] = field(default_factory=dict)
    transition_probability: float = 0.0


@dataclass(frozen=True)
class RegimeTransition:
    """Regime transition record.

    Attributes:
        from_regime: Source regime.
        to_regime:   Target regime.
        probability: Transition probability.
        timestamp:   Transition timestamp.
    """

    from_regime: RegimeType
    to_regime: RegimeType
    probability: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now().astimezone())


@dataclass(frozen=True)
class RegimeResult:
    """Complete regime detection result.

    Attributes:
        timestamp:      Detection timestamp.
        regime:         Current regime.
        score:          Regime score with confidence.
        features:       Extracted features.
        detector:       Detector used.
        recommendations: Adaptive recommendations.
        elapsed:        Detection time in seconds.
    """

    timestamp: datetime = field(default_factory=lambda: datetime.now().astimezone())
    regime: RegimeType = RegimeType.UNKNOWN
    score: RegimeScore = field(default_factory=RegimeScore)
    features: RegimeFeatures = field(default_factory=RegimeFeatures)
    detector: str = ""
    recommendations: dict[str, str] = field(default_factory=dict)
    elapsed: float = 0.0


@dataclass(frozen=True)
class RegimeHistory:
    """Historical regime detection results.

    Attributes:
        results:      Ordered regime results.
        transitions:  Regime transitions.
        current:      Current regime result.
        total_periods: Total periods covered.
    """

    results: tuple[RegimeResult, ...] = field(default_factory=tuple)
    transitions: tuple[RegimeTransition, ...] = field(default_factory=tuple)
    current: RegimeResult | None = None
    total_periods: int = 0


@dataclass(frozen=True)
class RegimeStatistics:
    """Regime detection statistics.

    Attributes:
        total_detections:   Total detections performed.
        regime_counts:      Count of each regime detected.
        regime_durations:   Average duration of each regime.
        transition_count:   Total transitions.
        most_common:        Most frequently detected regime.
        regime_stability:   Stability score (0 to 1).
        detector_performance: Detector performance metrics.
        warnings:           Detection warnings.
    """

    total_detections: int = 0
    regime_counts: dict[str, int] = field(default_factory=dict)
    regime_durations: dict[str, float] = field(default_factory=dict)
    transition_count: int = 0
    most_common: str = "UNKNOWN"
    regime_stability: float = 0.0
    detector_performance: dict[str, float] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@runtime_checkable
class RegimeDetector(Protocol):
    """Protocol for regime detectors."""

    @property
    def name(self) -> str:
        """Detector name."""
        ...

    def detect(
        self,
        features: RegimeFeatures,
        config: RegimeConfig,
    ) -> RegimeScore:
        """Detect market regime from features.

        Args:
            features: Extracted market features.
            config:   Regime configuration.

        Returns:
            RegimeScore with detected regime and confidence.
        """
        ...

    def confidence(
        self,
        features: RegimeFeatures,
        score: RegimeScore,
    ) -> float:
        """Compute confidence for a detection result.

        Args:
            features: Market features.
            score:    Regime score.

        Returns:
            Confidence value (0 to 1).
        """
        ...

    def diagnostics(
        self,
        history: tuple[RegimeResult, ...],
    ) -> dict[str, float]:
        """Compute detector diagnostics from history.

        Args:
            history: Historical detection results.

        Returns:
            Dict of diagnostic metrics.
        """
        ...


# ---------------------------------------------------------------------------
# Legacy / backward-compatible models (used by strategy/composite engines)
# ---------------------------------------------------------------------------

class Regime(StrEnum):
    """Legacy market regime classification (backward compatibility)."""

    STRONG_BULL = "Strong Bull"
    BULL = "Bull"
    NEUTRAL = "Neutral"
    WEAK = "Weak"
    BEAR = "Bear"


@dataclass(frozen=True)
class IndexData:
    """Legacy index data snapshot (backward compatibility)."""

    name: str = ""
    current_price: float = 0.0
    ema20: float | None = None
    ema50: float | None = None
    sma200: float | None = None
    rsi14: float | None = None
    macd_bullish: bool | None = None


@dataclass(frozen=True)
class BreadthData:
    """Legacy market breadth data (backward compatibility)."""

    percent_above_50dma: float | None = None
    percent_above_200dma: float | None = None


@dataclass(frozen=True)
class MarketSnapshot:
    """Legacy complete market snapshot (backward compatibility)."""

    nifty50: IndexData = field(default_factory=lambda: IndexData(name="Nifty 50"))
    nifty_midcap: IndexData = field(default_factory=lambda: IndexData(name="Nifty Midcap 150"))
    nifty_smallcap: IndexData = field(default_factory=lambda: IndexData(name="Nifty Smallcap 250"))
    breadth: BreadthData = field(default_factory=BreadthData)
    india_vix: float | None = None


@dataclass(frozen=True)
class MarketRegime:
    """Legacy market regime result (backward compatibility)."""

    regime: Regime = Regime.NEUTRAL
    confidence: float = 0.0
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
