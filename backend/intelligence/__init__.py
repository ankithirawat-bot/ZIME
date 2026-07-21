"""Adaptive Intelligence Platform.

Continuously evaluates models, strategies, and signals; automatically
selects best performers; builds ensembles; and provides explainable
confidence scores for investment decisions.
"""

from __future__ import annotations

from backend.intelligence.confidence import ConfidenceEngine
from backend.intelligence.ensemble import EnsembleEngine
from backend.intelligence.evaluation import MetricsCalculator
from backend.intelligence.exceptions import (
    ConfidenceError,
    EnsembleError,
    EvaluationError,
    InsufficientDataError,
    IntelligenceError,
    LearningError,
    ModelNotFoundError,
    SelectionError,
)
from backend.intelligence.factory import IntelligenceFactory
from backend.intelligence.learning import LearningEngine
from backend.intelligence.models import (
    AdaptiveRecommendation,
    ChallengerModel,
    ChampionModel,
    ConfidenceScore,
    EnsembleModel,
    EnsembleResult,
    EvaluationRequest,
    EvaluationResult,
    IntelligenceConfig,
    IntelligenceMetadata,
    PerformanceHistory,
    SelectionCriterion,
    WeightingStrategy,
)
from backend.intelligence.selection import ChampionChallengerSelector

__all__ = [
    "AdaptiveRecommendation",
    "ChampionChallengerSelector",
    "ChampionModel",
    "ChallengerModel",
    "ConfidenceEngine",
    "ConfidenceError",
    "ConfidenceScore",
    "EnsembleEngine",
    "EnsembleError",
    "EnsembleModel",
    "EnsembleResult",
    "EvaluationError",
    "EvaluationRequest",
    "EvaluationResult",
    "InsufficientDataError",
    "IntelligenceConfig",
    "IntelligenceError",
    "IntelligenceFactory",
    "IntelligenceMetadata",
    "LearningEngine",
    "LearningError",
    "MetricsCalculator",
    "ModelNotFoundError",
    "PerformanceHistory",
    "SelectionCriterion",
    "SelectionError",
    "WeightingStrategy",
]
