"""
Simple Moving Average (SMA) factor.
"""

from __future__ import annotations

from datetime import date
from typing import Any, ClassVar

import pandas as pd

from backend.core.enums import FactorCategory, Signal
from backend.core.factor_result import FactorResult
from backend.factors.base import BaseFactor
from backend.factors.registry import FactorRegistry


class SMA(BaseFactor):
    """Simple Moving Average price factor.

    Computes the arithmetic mean of closing prices over a configurable
    lookback window. The signal is derived by comparing the latest
    closing price to the SMA value:

    - Close > SMA  -> BULLISH
    - Close < SMA  -> BEARISH
    - Close == SMA -> NEUTRAL

    The factor type is registered in the FactorRegistry under the name
    ``"sma"``. The period is configurable at instantiation time.

    Args:
        period: Number of trading days in the moving average window.
                Must be a positive integer. Defaults to 20.

    Required kwargs for compute():

        prices (pd.DataFrame): Historical price data with at minimum
            a ``close`` column and a DatetimeIndex. The DataFrame must
            contain at least ``period`` rows of non-NaN closing prices.

    Example::

        >>> import pandas as pd
        >>> sma = SMA(period=20)
        >>> result = sma.compute(symbol="RELIANCE", prices=price_df)
        >>> result.value
        2456.78
        >>> result.signal
        <Signal.BULLISH: 'bullish'>

        # Discover via registry
        >>> from backend.factors.registry import FactorRegistry
        >>> FactorRegistry.get("sma")
        <class 'backend.factors.price.SMA'>
    """

    name: ClassVar[str] = "sma"
    display_name: ClassVar[str] = "SMA"
    category: ClassVar[FactorCategory] = FactorCategory.TECHNICAL

    def __init__(self, period: int = 20) -> None:
        """Initialize SMA with a configurable lookback period.

        Args:
            period: Number of trading days. Must be >= 1.

        Raises:
            ValueError: If period is less than 1.
        """
        if period < 1:
            raise ValueError(
                f"SMA period must be >= 1, got {period}"
            )
        self._period: int = period

    @property
    def period(self) -> int:
        """Return the lookback period.

        Returns:
            The number of trading days used in the moving average.
        """
        return self._period

    def compute(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Compute the SMA and compare latest close to it.

        Args:
            symbol: Ticker symbol of the instrument.
            **kwargs: Must contain ``prices`` -- a pandas DataFrame
                      with a ``close`` column and DatetimeIndex.

        Returns:
            A FactorResult with the SMA value, directional signal,
            and metadata containing the SMA value and latest close.

        Raises:
            No exceptions propagate. Insufficient or invalid data
            returns a neutral result with value=None.
        """
        try:
            return self._compute_impl(symbol, **kwargs)
        except Exception as exc:
            return FactorResult(
                factor_name=f"sma_{self._period}",
                factor_category=self.category,
                symbol=symbol,
                value=None,
                signal=Signal.NEUTRAL,
                as_of=date.today(),
                metadata={"error": str(exc)},
            )

    def _compute_impl(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Internal computation. Separated from compute() for safety.

        Args:
            symbol: Ticker symbol.
            **kwargs: Must contain ``prices`` DataFrame.

        Returns:
            FactorResult with computed SMA.

        Raises:
            ValueError: If prices is missing, wrong type, or has
                        insufficient data.
        """
        prices = kwargs.get("prices")
        if prices is None:
            raise ValueError("Missing required kwarg: prices")

        if not isinstance(prices, pd.DataFrame):
            raise TypeError(
                f"prices must be a pandas DataFrame, "
                f"got {type(prices).__name__}"
            )

        if "close" not in prices.columns:
            raise ValueError(
                f"prices DataFrame must contain a 'close' column. "
                f"Found: {list(prices.columns)}"
            )

        close = prices["close"].dropna()

        if len(close) < self._period:
            raise ValueError(
                f"Insufficient data: need {self._period} closing prices, "
                f"got {len(close)}"
            )

        sma_value = float(close.tail(self._period).mean())
        latest_close = float(close.iloc[-1])
        as_of = close.index[-1].date()

        if latest_close > sma_value:
            signal = Signal.BULLISH
        elif latest_close < sma_value:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        return FactorResult(
            factor_name=f"sma_{self._period}",
            factor_category=self.category,
            symbol=symbol,
            value=sma_value,
            signal=signal,
            as_of=as_of,
            metadata={
                "period": self._period,
                "sma_value": sma_value,
                "latest_close": latest_close,
            },
        )

    def __repr__(self) -> str:
        """Return developer-friendly representation.

        Returns:
            String like SMA(name='sma', category=<FactorCategory.TECHNICAL: 'technical'>).
        """
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, category={self.category!r})"
        )


# Register the SMA factor TYPE in the global registry.
# The period is configurable at instantiation: SMA(period=50).
FactorRegistry.register(SMA)
