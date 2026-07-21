"""Market regime detection engine.

Core engine for detecting market regimes and providing adaptive
recommendations to all other engines.
"""

from __future__ import annotations

import time
from typing import Any

from backend.regime.detectors import (
    HMMPlaceholderDetector,
    MLPlaceholderDetector,
    RuleBasedDetector,
    ScoreBasedDetector,
    VotingDetector,
)
from backend.regime.exceptions import DetectorNotFoundError
from backend.regime.features import FeatureExtractor
from backend.regime.models import (
    RegimeConfig,
    RegimeHistory,
    RegimeResult,
    RegimeScore,
    RegimeStatistics,
    RegimeTransition,
    RegimeType,
)
from backend.regime.scoring import (
    build_transition_matrix,
    compute_regime_statistics,
    compute_transition_probability,
    get_recommendations,
)


def _default_detectors() -> dict[str, Any]:
    """Create default regime detectors."""
    return {
        "rule_based": RuleBasedDetector(),
        "score_based": ScoreBasedDetector(),
        "voting": VotingDetector(),
        "hmm": HMMPlaceholderDetector(),
        "ml": MLPlaceholderDetector(),
    }


class RegimeEngine:
    """Core market regime detection engine.

    Detects market regimes from price and volume data, computes
    confidence scores, and provides adaptive recommendations
    for strategy, sizing, portfolio, risk, and volatility engines.
    """

    def __init__(
        self,
        config: RegimeConfig | None = None,
        detectors: dict[str, Any] | None = None,
        feature_extractor: FeatureExtractor | None = None,
        strategy_engine: Any | None = None,
        sizing_engine: Any | None = None,
        portfolio_engine: Any | None = None,
        risk_engine: Any | None = None,
        volatility_engine: Any | None = None,
        backtesting_engine: Any | None = None,
    ) -> None:
        """Initialize the engine.

        Args:
            config:             Configuration (defaults created).
            detectors:          Detectors (defaults created).
            feature_extractor:  Feature extractor (defaults created).
            strategy_engine:    Optional strategy engine.
            sizing_engine:      Optional sizing engine.
            portfolio_engine:   Optional portfolio engine.
            risk_engine:        Optional risk engine.
            volatility_engine:  Optional volatility engine.
            backtesting_engine: Optional backtesting engine.
        """
        self._config = config or RegimeConfig()
        self._detectors = detectors or _default_detectors()
        self._feature_extractor = feature_extractor or FeatureExtractor()
        self._strategy_engine = strategy_engine
        self._sizing_engine = sizing_engine
        self._portfolio_engine = portfolio_engine
        self._risk_engine = risk_engine
        self._volatility_engine = volatility_engine
        self._backtesting_engine = backtesting_engine
        self._history: list[RegimeResult] = []
        self._last_regime: RegimeType | None = None
        self._total_detections = 0

    @property
    def config(self) -> RegimeConfig:
        """Current configuration."""
        return self._config

    @property
    def history(self) -> tuple[RegimeResult, ...]:
        """Detection history."""
        return tuple(self._history)

    def _get_detector(self, name: str | None = None) -> Any:
        detector_name = name or self._config.detector
        if detector_name not in self._detectors:
            raise DetectorNotFoundError(detector_name)
        return self._detectors[detector_name]

    def detect(
        self,
        prices: tuple[float, ...],
        volumes: tuple[float, ...] | None = None,
        advances: tuple[float, ...] | None = None,
        declines: tuple[float, ...] | None = None,
        returns_map: dict[str, tuple[float, ...]] | None = None,
        spreads: tuple[float, ...] | None = None,
        detector_name: str | None = None,
        config: RegimeConfig | None = None,
    ) -> RegimeResult:
        """Detect current market regime.

        Args:
            prices:         Price series.
            volumes:        Volume series.
            advances:       Advance count series.
            declines:       Decline count series.
            returns_map:    Symbol -> returns for correlation/dispersion.
            spreads:        Bid-ask spread series.
            detector_name:  Detector override.
            config:         Configuration override.

        Returns:
            RegimeResult with detected regime.
        """
        cfg = config or self._config
        detector = self._get_detector(detector_name)
        start = time.perf_counter()

        features = self._feature_extractor.extract(
            prices, volumes, advances, declines, returns_map, spreads, cfg
        )

        score = detector.detect(features, cfg)

        if self._last_regime is not None:
            trans_prob = compute_transition_probability(
                score.regime, self._last_regime, features, score
            )
            score = RegimeScore(
                regime=score.regime,
                confidence=score.confidence,
                evidence=score.evidence,
                competing_regimes=score.competing_regimes,
                transition_probability=trans_prob,
            )

        recommendations = get_recommendations(score.regime)
        elapsed = time.perf_counter() - start

        result = RegimeResult(
            regime=score.regime,
            score=score,
            features=features,
            detector=detector.name,
            recommendations=recommendations,
            elapsed=elapsed,
        )

        self._last_regime = score.regime
        self._history.append(result)
        self._total_detections += 1

        return result

    def detect_batch(
        self,
        price_series: tuple[tuple[float, ...], ...],
        volume_series: tuple[tuple[float, ...] | None, ...] | None = None,
        detector_name: str | None = None,
        config: RegimeConfig | None = None,
    ) -> RegimeHistory:
        """Detect regimes across multiple time windows.

        Args:
            price_series:  Tuple of price windows.
            volume_series: Tuple of volume windows.
            detector_name: Detector override.
            config:        Configuration override.

        Returns:
            RegimeHistory with all detection results.
        """
        cfg = config or self._config
        results: list[RegimeResult] = []

        for i, prices in enumerate(price_series):
            volumes = volume_series[i] if volume_series and i < len(volume_series) else None
            result = self.detect(
                prices=prices,
                volumes=volumes,
                detector_name=detector_name,
                config=cfg,
            )
            results.append(result)

        return self._build_history(tuple(results))

    def detect_history(
        self,
        prices: tuple[float, ...],
        window: int = 252,
        step: int = 20,
        volumes: tuple[float, ...] | None = None,
        detector_name: str | None = None,
        config: RegimeConfig | None = None,
    ) -> RegimeHistory:
        """Detect regimes over historical rolling windows.

        Args:
            prices:         Full price series.
            window:         Rolling window size.
            step:           Step between windows.
            volumes:        Full volume series.
            detector_name:  Detector override.
            config:         Configuration override.

        Returns:
            RegimeHistory with all detection results.
        """
        cfg = config or self._config
        results: list[RegimeResult] = []

        if len(prices) < window:
            return RegimeHistory()

        current_detector = self._last_regime
        self._last_regime = None

        for i in range(window, len(prices) + 1, step):
            end = min(i, len(prices))
            start_idx = end - window
            price_window = prices[start_idx:end]
            vol_window = None
            if volumes:
                vol_window = volumes[start_idx:end]

            result = self.detect(
                prices=price_window,
                volumes=vol_window,
                detector_name=detector_name,
                config=cfg,
            )
            results.append(result)

        self._last_regime = current_detector
        return self._build_history(tuple(results))

    def transition_matrix(
        self,
    ) -> dict[str, dict[str, float]]:
        """Build regime transition matrix from history.

        Returns:
            Transition matrix.
        """
        return build_transition_matrix(tuple(self._history))

    def regime_statistics(
        self,
    ) -> RegimeStatistics:
        """Compute regime detection statistics.

        Returns:
            RegimeStatistics.
        """
        return compute_regime_statistics(tuple(self._history))

    def _build_history(
        self,
        results: tuple[RegimeResult, ...],
    ) -> RegimeHistory:
        """Build RegimeHistory from results."""
        transitions: list[RegimeTransition] = []
        for i in range(1, len(results)):
            if results[i - 1].regime != results[i].regime:
                transitions.append(
                    RegimeTransition(
                        from_regime=results[i - 1].regime,
                        to_regime=results[i].regime,
                    )
                )

        return RegimeHistory(
            results=results,
            transitions=tuple(transitions),
            current=results[-1] if results else None,
            total_periods=len(results),
        )
