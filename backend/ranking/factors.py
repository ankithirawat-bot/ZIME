"""Built-in ranking factors.

Fundamental, technical, and quality factors for ranking securities.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.ranking.models import FactorCategory, RankingDirection

FactorFunc = Callable[[dict[str, Any]], float | None]


def _get_nested(data: dict[str, Any], key: str, default: float | None = None) -> float | None:
    """Get a value from nested dictionaries using dot notation."""
    parts = key.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part, default)
        else:
            return default
    if current is None:
        return default
    try:
        return float(current)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Fundamental Factors
# ---------------------------------------------------------------------------


def factor_roce(data: dict[str, Any]) -> float | None:
    """Get ROCE (Return on Capital Employed) value."""
    return _get_nested(data, "fundamentals.roce")


def factor_roe(data: dict[str, Any]) -> float | None:
    """Get ROE (Return on Equity) value."""
    return _get_nested(data, "fundamentals.roe")


def factor_sales_growth(data: dict[str, Any]) -> float | None:
    """Get Sales Growth percentage."""
    return _get_nested(data, "fundamentals.sales_growth")


def factor_profit_growth(data: dict[str, Any]) -> float | None:
    """Get Profit Growth percentage."""
    return _get_nested(data, "fundamentals.profit_growth")


def factor_eps_growth(data: dict[str, Any]) -> float | None:
    """Get EPS Growth percentage."""
    return _get_nested(data, "fundamentals.eps_growth")


def factor_debt_equity(data: dict[str, Any]) -> float | None:
    """Get Debt/Equity ratio."""
    return _get_nested(data, "fundamentals.debt_equity")


def factor_operating_margin(data: dict[str, Any]) -> float | None:
    """Get Operating Margin percentage."""
    return _get_nested(data, "fundamentals.operating_margin")


# ---------------------------------------------------------------------------
# Technical Factors
# ---------------------------------------------------------------------------


def factor_relative_strength(data: dict[str, Any]) -> float | None:
    """Get Relative Strength score."""
    return _get_nested(data, "technicals.rs_score")


def factor_trend_score(data: dict[str, Any]) -> float | None:
    """Get Trend Score."""
    return _get_nested(data, "technicals.trend_score")


def factor_momentum_score(data: dict[str, Any]) -> float | None:
    """Get Momentum Score."""
    return _get_nested(data, "technicals.momentum_score")


def factor_volume_score(data: dict[str, Any]) -> float | None:
    """Get Volume Score."""
    return _get_nested(data, "technicals.volume_score")


def factor_volatility_score(data: dict[str, Any]) -> float | None:
    """Get Volatility Score."""
    return _get_nested(data, "technicals.volatility_score")


# ---------------------------------------------------------------------------
# Quality Factors
# ---------------------------------------------------------------------------


def factor_data_quality_confidence(data: dict[str, Any]) -> float | None:
    """Get Data Quality Confidence score."""
    return _get_nested(data, "quality.data_confidence")


def factor_liquidity_score(data: dict[str, Any]) -> float | None:
    """Get Liquidity Score."""
    return _get_nested(data, "quality.liquidity_score")


# ---------------------------------------------------------------------------
# Built-in factor definitions
# ---------------------------------------------------------------------------


BUILTIN_FACTORS: dict[str, tuple[FactorCategory, RankingDirection, FactorFunc]] = {
    # Fundamental
    "roce": (FactorCategory.FUNDAMENTAL, RankingDirection.HIGHER_IS_BETTER, factor_roce),
    "roe": (FactorCategory.FUNDAMENTAL, RankingDirection.HIGHER_IS_BETTER, factor_roe),
    "sales_growth": (FactorCategory.FUNDAMENTAL, RankingDirection.HIGHER_IS_BETTER, factor_sales_growth),
    "profit_growth": (FactorCategory.FUNDAMENTAL, RankingDirection.HIGHER_IS_BETTER, factor_profit_growth),
    "eps_growth": (FactorCategory.FUNDAMENTAL, RankingDirection.HIGHER_IS_BETTER, factor_eps_growth),
    "debt_equity": (FactorCategory.FUNDAMENTAL, RankingDirection.LOWER_IS_BETTER, factor_debt_equity),
    "operating_margin": (FactorCategory.FUNDAMENTAL, RankingDirection.HIGHER_IS_BETTER, factor_operating_margin),
    # Technical
    "relative_strength": (FactorCategory.TECHNICAL, RankingDirection.HIGHER_IS_BETTER, factor_relative_strength),
    "trend_score": (FactorCategory.TECHNICAL, RankingDirection.HIGHER_IS_BETTER, factor_trend_score),
    "momentum_score": (FactorCategory.TECHNICAL, RankingDirection.HIGHER_IS_BETTER, factor_momentum_score),
    "volume_score": (FactorCategory.TECHNICAL, RankingDirection.HIGHER_IS_BETTER, factor_volume_score),
    "volatility_score": (FactorCategory.TECHNICAL, RankingDirection.LOWER_IS_BETTER, factor_volatility_score),
    # Quality
    "data_quality_confidence": (FactorCategory.QUALITY, RankingDirection.HIGHER_IS_BETTER, factor_data_quality_confidence),
    "liquidity_score": (FactorCategory.QUALITY, RankingDirection.HIGHER_IS_BETTER, factor_liquidity_score),
}


def get_builtin_factors() -> dict[str, tuple[FactorCategory, RankingDirection, FactorFunc]]:
    """Return a copy of the built-in factor registry."""
    return dict(BUILTIN_FACTORS)
