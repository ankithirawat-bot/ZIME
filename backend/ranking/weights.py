"""Weight validation and management for ranking factors.

Ensures weights total 100% and provides validation utilities.
"""

from __future__ import annotations

from backend.ranking.exceptions import InvalidWeightsError
from backend.ranking.models import RankingFactor


def validate_weights(factors: tuple[RankingFactor, ...], tolerance: float = 0.001) -> bool:
    """Validate that factor weights total 1.0 (100%).

    Args:
        factors:   Tuple of ranking factors.
        tolerance: Tolerance for floating-point comparison.

    Returns:
        True if weights are valid.

    Raises:
        InvalidWeightsError: If weights are invalid.
    """
    if not factors:
        raise InvalidWeightsError("No factors provided")

    total_weight = sum(f.weight for f in factors)

    if abs(total_weight - 1.0) > tolerance:
        raise InvalidWeightsError(
            f"Weights must total 1.0 (100%), got {total_weight:.4f}"
        )

    for factor in factors:
        if factor.weight < 0:
            raise InvalidWeightsError(
                f"Weight for '{factor.name}' must be non-negative, got {factor.weight}"
            )
        if factor.weight > 1.0:
            raise InvalidWeightsError(
                f"Weight for '{factor.name}' must be <= 1.0, got {factor.weight}"
            )

    return True


def normalize_weights(factors: tuple[RankingFactor, ...]) -> tuple[RankingFactor, ...]:
    """Normalize weights to sum to 1.0.

    Args:
        factors: Tuple of ranking factors.

    Returns:
        Tuple of factors with normalized weights.
    """
    if not factors:
        return ()

    total_weight = sum(f.weight for f in factors)
    if total_weight == 0:
        equal_weight = 1.0 / len(factors)
        return tuple(
            RankingFactor(
                name=f.name,
                weight=equal_weight,
                category=f.category,
                direction=f.direction,
                normalization=f.normalization,
                description=f.description,
            )
            for f in factors
        )

    return tuple(
        RankingFactor(
            name=f.name,
            weight=f.weight / total_weight,
            category=f.category,
            direction=f.direction,
            normalization=f.normalization,
            description=f.description,
        )
        for f in factors
    )


def equalize_weights(factors: tuple[RankingFactor, ...]) -> tuple[RankingFactor, ...]:
    """Set equal weights for all factors.

    Args:
        factors: Tuple of ranking factors.

    Returns:
        Tuple of factors with equal weights.
    """
    if not factors:
        return ()

    equal_weight = 1.0 / len(factors)
    return tuple(
        RankingFactor(
            name=f.name,
            weight=equal_weight,
            category=f.category,
            direction=f.direction,
            normalization=f.normalization,
            description=f.description,
        )
        for f in factors
    )


def get_weight_dict(factors: tuple[RankingFactor, ...]) -> dict[str, float]:
    """Convert factors to a weight dictionary.

    Args:
        factors: Tuple of ranking factors.

    Returns:
        Dictionary mapping factor names to weights.
    """
    return {f.name: f.weight for f in factors}


def apply_weights(
    normalized_scores: dict[str, float],
    weights: dict[str, float],
) -> float:
    """Apply weights to normalized scores.

    Args:
        normalized_scores: Dictionary of factor names to normalized scores.
        weights:           Dictionary of factor names to weights.

    Returns:
        Total weighted score.
    """
    total = 0.0
    for factor_name, score in normalized_scores.items():
        weight = weights.get(factor_name, 0.0)
        total += score * weight
    return total
