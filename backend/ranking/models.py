"""Ranking models.

Frozen dataclasses for ranking definitions, factor scores,
and results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class FactorCategory(StrEnum):
    """Categories of ranking factors."""

    FUNDAMENTAL = "fundamental"
    TECHNICAL = "technical"
    QUALITY = "quality"
    CUSTOM = "custom"


class NormalizationMethod(StrEnum):
    """Normalization methods for factor scores."""

    MIN_MAX = "min_max"
    Z_SCORE = "z_score"
    PERCENTILE = "percentile"


class RankingDirection(StrEnum):
    """Direction for ranking (higher is better or lower is better)."""

    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


@dataclass(frozen=True)
class RankingMetadata:
    """Metadata for a ranking definition.

    Attributes:
        name:        Ranking name.
        description: Ranking description.
        version:     Schema version.
        author:      Ranking author.
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
class RankingFactor:
    """Definition of a ranking factor.

    Attributes:
        name:        Factor name.
        weight:      Factor weight (0.0 to 1.0).
        category:    Factor category.
        direction:   Ranking direction.
        normalization: Normalization method.
        description: Factor description.
    """

    name: str
    weight: float = 0.0
    category: FactorCategory = FactorCategory.CUSTOM
    direction: RankingDirection = RankingDirection.HIGHER_IS_BETTER
    normalization: NormalizationMethod = NormalizationMethod.MIN_MAX
    description: str = ""


@dataclass(frozen=True)
class FactorScore:
    """Score for a single factor.

    Attributes:
        factor_name:  Factor name.
        symbol:       Ticker symbol.
        raw_value:    Raw factor value.
        normalized:   Normalized score (0.0 to 1.0).
        weight:       Factor weight.
        weighted:     Weighted score.
    """

    factor_name: str
    symbol: str
    raw_value: float
    normalized: float = 0.0
    weight: float = 0.0
    weighted: float = 0.0


@dataclass(frozen=True)
class RankingEntry:
    """A single ranking entry.

    Attributes:
        symbol:       Ticker symbol.
        rank:         Rank position (1-based).
        total_score:  Total weighted score.
        factor_scores: Individual factor scores.
    """

    symbol: str
    rank: int = 0
    total_score: float = 0.0
    factor_scores: tuple[FactorScore, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RankingStatistics:
    """Statistics for a ranking run.

    Attributes:
        total_symbols:  Total symbols ranked.
        total_factors:  Total factors used.
        elapsed_seconds: Ranking execution time.
        mean_score:     Mean total score.
        median_score:   Median total score.
        std_score:      Standard deviation of scores.
    """

    total_symbols: int = 0
    total_factors: int = 0
    elapsed_seconds: float = 0.0
    mean_score: float = 0.0
    median_score: float = 0.0
    std_score: float = 0.0


@dataclass(frozen=True)
class RankingDefinition:
    """Complete ranking definition.

    Attributes:
        metadata:      Ranking metadata.
        factors:       Ranking factors.
        normalization: Default normalization method.
    """

    metadata: RankingMetadata
    factors: tuple[RankingFactor, ...] = field(default_factory=tuple)
    normalization: NormalizationMethod = NormalizationMethod.MIN_MAX


@dataclass(frozen=True)
class RankingResult:
    """Result of a ranking evaluation.

    Attributes:
        ranking_name:  Name of the ranking used.
        entries:       Ranked entries (highest score first).
        statistics:    Ranking statistics.
        evaluated_at:  When the evaluation was performed.
    """

    ranking_name: str
    entries: tuple[RankingEntry, ...] = field(default_factory=tuple)
    statistics: RankingStatistics = field(default_factory=RankingStatistics)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
