"""Screener filters.

Built-in filters for fundamental, technical, price, and liquidity screening.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.screener.models import EvaluationContext, FilterCategory

FilterFunc = Callable[[EvaluationContext], Any]


def _get_nested(data: dict[str, Any], key: str, default: Any = None) -> Any:
    """Get a value from nested dictionaries using dot notation."""
    parts = key.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part, default)
        else:
            return default
    return current


# ---------------------------------------------------------------------------
# Fundamental Filters
# ---------------------------------------------------------------------------


def filter_market_cap(ctx: EvaluationContext) -> Any:
    """Get market cap value."""
    return _get_nested(ctx.fundamentals, "market_cap", 0)


def filter_sales_growth(ctx: EvaluationContext) -> Any:
    """Get sales growth percentage."""
    return _get_nested(ctx.fundamentals, "sales_growth", 0)


def filter_profit_growth(ctx: EvaluationContext) -> Any:
    """Get profit growth percentage."""
    return _get_nested(ctx.fundamentals, "profit_growth", 0)


def filter_eps_growth(ctx: EvaluationContext) -> Any:
    """Get EPS growth percentage."""
    return _get_nested(ctx.fundamentals, "eps_growth", 0)


def filter_roe(ctx: EvaluationContext) -> Any:
    """Get Return on Equity percentage."""
    return _get_nested(ctx.fundamentals, "roe", 0)


def filter_roce(ctx: EvaluationContext) -> Any:
    """Get Return on Capital Employed percentage."""
    return _get_nested(ctx.fundamentals, "roce", 0)


def filter_debt_equity(ctx: EvaluationContext) -> Any:
    """Get Debt/Equity ratio."""
    return _get_nested(ctx.fundamentals, "debt_equity", 0)


# ---------------------------------------------------------------------------
# Technical Filters
# ---------------------------------------------------------------------------


def filter_trend_state(ctx: EvaluationContext) -> Any:
    """Get trend state string."""
    return _get_nested(ctx.technicals, "trend_state", "Unknown")


def filter_momentum_state(ctx: EvaluationContext) -> Any:
    """Get momentum state string."""
    return _get_nested(ctx.technicals, "momentum_state", "Unknown")


def filter_relative_strength_state(ctx: EvaluationContext) -> Any:
    """Get relative strength state string."""
    return _get_nested(ctx.technicals, "rs_state", "Unknown")


def filter_volume_state(ctx: EvaluationContext) -> Any:
    """Get volume state string."""
    return _get_nested(ctx.technicals, "volume_state", "Unknown")


def filter_volatility_state(ctx: EvaluationContext) -> Any:
    """Get volatility state string."""
    return _get_nested(ctx.technicals, "volatility_state", "Unknown")


# ---------------------------------------------------------------------------
# Price Filters
# ---------------------------------------------------------------------------


def filter_close(ctx: EvaluationContext) -> Any:
    """Get close price."""
    return _get_nested(ctx.price_data, "close", 0)


def filter_ema20(ctx: EvaluationContext) -> Any:
    """Get EMA20 value."""
    return _get_nested(ctx.price_data, "ema20", 0)


def filter_ema50(ctx: EvaluationContext) -> Any:
    """Get EMA50 value."""
    return _get_nested(ctx.price_data, "ema50", 0)


def filter_ema200(ctx: EvaluationContext) -> Any:
    """Get EMA200 value."""
    return _get_nested(ctx.price_data, "ema200", 0)


def filter_atr(ctx: EvaluationContext) -> Any:
    """Get ATR (Average True Range) value."""
    return _get_nested(ctx.price_data, "atr", 0)


def filter_52_week_high(ctx: EvaluationContext) -> Any:
    """Get 52-week high price."""
    return _get_nested(ctx.price_data, "high_52w", 0)


def filter_52_week_low(ctx: EvaluationContext) -> Any:
    """Get 52-week low price."""
    return _get_nested(ctx.price_data, "low_52w", 0)


# ---------------------------------------------------------------------------
# Liquidity Filters
# ---------------------------------------------------------------------------


def filter_average_volume(ctx: EvaluationContext) -> Any:
    """Get average volume."""
    return _get_nested(ctx.liquidity_data, "avg_volume", 0)


def filter_delivery_pct(ctx: EvaluationContext) -> Any:
    """Get delivery percentage."""
    return _get_nested(ctx.liquidity_data, "delivery_pct", 0)


def filter_traded_value(ctx: EvaluationContext) -> Any:
    """Get traded value."""
    return _get_nested(ctx.liquidity_data, "traded_value", 0)


# ---------------------------------------------------------------------------
# Built-in filter registry
# ---------------------------------------------------------------------------


_BUILTIN_FILTERS: dict[str, tuple[FilterCategory, FilterFunc]] = {
    # Fundamental
    "market_cap": (FilterCategory.FUNDAMENTAL, filter_market_cap),
    "sales_growth": (FilterCategory.FUNDAMENTAL, filter_sales_growth),
    "profit_growth": (FilterCategory.FUNDAMENTAL, filter_profit_growth),
    "eps_growth": (FilterCategory.FUNDAMENTAL, filter_eps_growth),
    "roe": (FilterCategory.FUNDAMENTAL, filter_roe),
    "roce": (FilterCategory.FUNDAMENTAL, filter_roce),
    "debt_equity": (FilterCategory.FUNDAMENTAL, filter_debt_equity),
    # Technical
    "trend_state": (FilterCategory.TECHNICAL, filter_trend_state),
    "momentum_state": (FilterCategory.TECHNICAL, filter_momentum_state),
    "rs_state": (FilterCategory.TECHNICAL, filter_relative_strength_state),
    "volume_state": (FilterCategory.TECHNICAL, filter_volume_state),
    "volatility_state": (FilterCategory.TECHNICAL, filter_volatility_state),
    # Price
    "close": (FilterCategory.PRICE, filter_close),
    "ema20": (FilterCategory.PRICE, filter_ema20),
    "ema50": (FilterCategory.PRICE, filter_ema50),
    "ema200": (FilterCategory.PRICE, filter_ema200),
    "atr": (FilterCategory.PRICE, filter_atr),
    "high_52w": (FilterCategory.PRICE, filter_52_week_high),
    "low_52w": (FilterCategory.PRICE, filter_52_week_low),
    # Liquidity
    "avg_volume": (FilterCategory.LIQUIDITY, filter_average_volume),
    "delivery_pct": (FilterCategory.LIQUIDITY, filter_delivery_pct),
    "traded_value": (FilterCategory.LIQUIDITY, filter_traded_value),
}


def get_builtin_filters() -> dict[str, tuple[FilterCategory, FilterFunc]]:
    """Return a copy of the built-in filter registry."""
    return dict(_BUILTIN_FILTERS)
