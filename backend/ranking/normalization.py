"""Normalization methods for ranking factors.

Supports Min-Max, Z-Score, and Percentile Rank normalization.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from backend.ranking.exceptions import InvalidNormalizationError
from backend.ranking.models import NormalizationMethod, RankingDirection


def normalize_min_max(values: Sequence[float]) -> tuple[float, ...]:
    """Normalize values using Min-Max normalization.

    Maps values to [0, 1] range.

    Args:
        values: Raw values to normalize.

    Returns:
        Tuple of normalized values.
    """
    if not values:
        return ()

    min_val = min(values)
    max_val = max(values)
    range_val = max_val - min_val

    if range_val == 0:
        return tuple(0.5 for _ in values)

    return tuple((v - min_val) / range_val for v in values)


def normalize_z_score(values: Sequence[float]) -> tuple[float, ...]:
    """Normalize values using Z-Score normalization.

    Maps values to have mean=0, std=1.

    Args:
        values: Raw values to normalize.

    Returns:
        Tuple of normalized values.
    """
    if not values:
        return ()

    n = len(values)
    if n < 2:
        return tuple(0.0 for _ in values)

    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    std = math.sqrt(variance)

    if std == 0:
        return tuple(0.0 for _ in values)

    return tuple((v - mean) / std for v in values)


def normalize_percentile(values: Sequence[float]) -> tuple[float, ...]:
    """Normalize values using Percentile Rank normalization.

    Maps values to [0, 1] based on their percentile rank.

    Args:
        values: Raw values to normalize.

    Returns:
        Tuple of normalized values.
    """
    if not values:
        return ()

    n = len(values)
    if n < 2:
        return tuple(1.0 for _ in values)

    sorted_indices = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n

    for rank, idx in enumerate(sorted_indices):
        ranks[idx] = rank / (n - 1)

    return tuple(ranks)


def normalize(
    values: Sequence[float],
    method: NormalizationMethod,
    direction: RankingDirection = RankingDirection.HIGHER_IS_BETTER,
) -> tuple[float, ...]:
    """Normalize values using the specified method.

    Args:
        values:    Raw values to normalize.
        method:    Normalization method.
        direction: Ranking direction (affects sign for Z-Score).

    Returns:
        Tuple of normalized values.

    Raises:
        InvalidNormalizationError: If the method is invalid.
    """
    if method is NormalizationMethod.MIN_MAX:
        normalized = normalize_min_max(values)
    elif method is NormalizationMethod.Z_SCORE:
        normalized = normalize_z_score(values)
    elif method is NormalizationMethod.PERCENTILE:
        normalized = normalize_percentile(values)
    else:
        raise InvalidNormalizationError(method.value)

    if direction is RankingDirection.LOWER_IS_BETTER:
        normalized = tuple(1.0 - v for v in normalized)

    return normalized


def normalize_factor_scores(
    raw_values: tuple[float, ...],
    method: NormalizationMethod,
    direction: RankingDirection,
) -> tuple[float, ...]:
    """Normalize factor scores with direction handling.

    For LOWER_IS_BETTER direction, invert the normalized scores
    so that lower raw values produce higher normalized scores.

    Args:
        raw_values: Raw factor values.
        method:     Normalization method.
        direction:  Ranking direction.

    Returns:
        Tuple of normalized scores in [0, 1] range.
    """
    normalized = normalize(raw_values, method, direction)

    if method is NormalizationMethod.Z_SCORE:
        min_val = min(normalized)
        max_val = max(normalized)
        range_val = max_val - min_val
        if range_val > 0:
            normalized = tuple((v - min_val) / range_val for v in normalized)
        else:
            normalized = tuple(0.5 for _ in normalized)

    return normalized
