"""
Standardized result type for all factor computations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from backend.core.enums import FactorCategory, Signal


@dataclass(frozen=True)
class FactorResult:
    """Standardized output produced by every factor computation.

    This is the universal data contract between factors and the
    scoring/engine layers. Every factor -- whether technical,
    fundamental, risk, liquidity, or ML-based -- must return an
    instance of this class.

    Attributes:
        factor_name:    Unique machine-readable identifier of the factor
                        that produced this result (e.g. "sma_20", "roe_ttm").
        factor_category:
                        The analytical domain this factor belongs to.
        symbol:         Ticker symbol of the instrument (e.g. "RELIANCE").
        value:          Primary numeric result. None indicates the factor
                        could not compute (e.g. insufficient data).
        signal:         Directional interpretation of the value by the
                        factor's internal logic.
        as_of:          The date the underlying data is current to.
        confidence:     Optional confidence score in the range [0.0, 1.0].
                        None means the factor does not produce confidence.
        metadata:       Arbitrary dictionary for factor-specific data.
                        Examples: sector medians for fundamental factors,
                        component values for composite factors, model
                        version for ML factors.

    Example:

        >>> from datetime import date
        >>> result = FactorResult(
        ...     factor_name="roe_ttm",
        ...     factor_category=FactorCategory.FUNDAMENTAL,
        ...     symbol="RELIANCE",
        ...     value=9.8,
        ...     signal=Signal.BEARISH,
        ...     as_of=date(2025, 12, 31),
        ...     confidence=0.85,
        ...     metadata={"sector_median": 14.2},
        ... )
        >>> result.factor_name
        'roe_ttm'
    """

    factor_name: str
    factor_category: FactorCategory
    symbol: str
    value: float | None
    signal: Signal
    as_of: date
    confidence: float | None = None
    metadata: dict[str, Any] | None = field(default=None)
