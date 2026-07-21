"""Market regime detection engine.

Provides institutional-grade market regime detection that continuously
identifies the current market environment and provides adaptive
recommendations to every other engine.
"""

from __future__ import annotations

from backend.regime.detectors import (
    HMMPlaceholderDetector,
    MLPlaceholderDetector,
    RuleBasedDetector,
    ScoreBasedDetector,
    VotingDetector,
)
from backend.regime.engine import RegimeEngine
from backend.regime.exceptions import (
    DetectionError,
    DetectorNotFoundError,
    FeatureError,
    InsufficientDataError,
    InvalidRegimeConfigError,
    RegimeError,
    TransitionError,
)
from backend.regime.factory import RegimeFactory
from backend.regime.features import FeatureExtractor
from backend.regime.models import (
    BreadthData,
    IndexData,
    MarketRegime,
    MarketSnapshot,
    Regime,
    RegimeConfig,
    RegimeFeatures,
    RegimeHistory,
    RegimeMetadata,
    RegimeResult,
    RegimeScore,
    RegimeStatistics,
    RegimeTransition,
    RegimeType,
)

__all__ = [
    "BreadthData",
    "DetectionError",
    "DetectorNotFoundError",
    "FeatureError",
    "FeatureExtractor",
    "HMMPlaceholderDetector",
    "IndexData",
    "InsufficientDataError",
    "InvalidRegimeConfigError",
    "MarketRegime",
    "MarketSnapshot",
    "MLPlaceholderDetector",
    "Regime",
    "RegimeConfig",
    "RegimeEngine",
    "RegimeError",
    "RegimeFactory",
    "RegimeFeatures",
    "RegimeHistory",
    "RegimeMetadata",
    "RegimeResult",
    "RegimeScore",
    "RegimeStatistics",
    "RegimeTransition",
    "RegimeType",
    "RuleBasedDetector",
    "ScoreBasedDetector",
    "TransitionError",
    "VotingDetector",
]
