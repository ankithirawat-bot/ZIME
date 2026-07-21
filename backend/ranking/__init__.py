"""
Universal Ranking & Scoring Engine.

Production-grade ranking engine for scoring securities using
configurable weighted factors.
"""

from backend.ranking.engine import RankingEngine
from backend.ranking.exceptions import (
    EmptyUniverseError,
    FactorNotFoundError,
    InsufficientDataError,
    InvalidNormalizationError,
    InvalidWeightsError,
    RankingConfigurationError,
    RankingError,
)
from backend.ranking.factory import RankingFactory
from backend.ranking.models import (
    FactorCategory,
    FactorScore,
    NormalizationMethod,
    RankingDefinition,
    RankingDirection,
    RankingEntry,
    RankingFactor,
    RankingMetadata,
    RankingResult,
    RankingStatistics,
)
from backend.ranking.normalization import (
    normalize,
    normalize_factor_scores,
    normalize_min_max,
    normalize_percentile,
    normalize_z_score,
)
from backend.ranking.registry import FactorRegistry, build_default_factor_registry
from backend.ranking.weights import (
    apply_weights,
    equalize_weights,
    get_weight_dict,
    normalize_weights,
    validate_weights,
)

__all__ = [
    "EmptyUniverseError",
    "FactorCategory",
    "FactorNotFoundError",
    "FactorRegistry",
    "FactorScore",
    "InsufficientDataError",
    "InvalidNormalizationError",
    "InvalidWeightsError",
    "NormalizationMethod",
    "RankingConfigurationError",
    "RankingDefinition",
    "RankingDirection",
    "RankingEngine",
    "RankingEntry",
    "RankingError",
    "RankingFactory",
    "RankingFactor",
    "RankingMetadata",
    "RankingResult",
    "RankingStatistics",
    "apply_weights",
    "build_default_factor_registry",
    "equalize_weights",
    "get_weight_dict",
    "normalize",
    "normalize_factor_scores",
    "normalize_min_max",
    "normalize_percentile",
    "normalize_weights",
    "normalize_z_score",
    "validate_weights",
]
