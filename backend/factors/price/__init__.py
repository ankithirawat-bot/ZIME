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


class EMA(BaseFactor):
    """Exponential Moving Average price factor.

    Computes the exponentially weighted mean of closing prices over a
    configurable lookback window. EMA gives more weight to recent prices,
    making it more responsive to new information than the SMA.

    The signal is derived by comparing the latest closing price to the
    EMA value:

    - Close > EMA  -> BULLISH
    - Close < EMA  -> BEARISH
    - Close == EMA -> NEUTRAL

    The factor type is registered in the FactorRegistry under the name
    ``"ema"``. The period is configurable at instantiation time.

    Uses ``pandas.DataFrame.ewm(span=period, adjust=False)`` for the
    recursive EMA calculation, which is the standard convention used
    by most charting platforms and technical analysis libraries.

    Args:
        period: Number of trading days for the EMA span. Must be a
                positive integer. Defaults to 20.

    Required kwargs for compute():

        prices (pd.DataFrame): Historical price data with at minimum
            a ``close`` column and a DatetimeIndex. The DataFrame must
            contain at least ``period`` rows of non-NaN closing prices.

    Example::

        >>> import pandas as pd
        >>> ema = EMA(period=20)
        >>> result = ema.compute(symbol="RELIANCE", prices=price_df)
        >>> result.value
        2458.12
        >>> result.signal
        <Signal.BULLISH: 'bullish'>

        # Discover via registry
        >>> from backend.factors.registry import FactorRegistry
        >>> FactorRegistry.get("ema")
        <class 'backend.factors.price.EMA'>
    """

    name: ClassVar[str] = "ema"
    display_name: ClassVar[str] = "EMA"
    category: ClassVar[FactorCategory] = FactorCategory.TECHNICAL

    def __init__(self, period: int = 20) -> None:
        """Initialize EMA with a configurable lookback period.

        Args:
            period: Number of trading days (span). Must be >= 1.

        Raises:
            ValueError: If period is less than 1.
        """
        if period < 1:
            raise ValueError(
                f"EMA period must be >= 1, got {period}"
            )
        self._period: int = period

    @property
    def period(self) -> int:
        """Return the lookback period.

        Returns:
            The number of trading days used in the EMA span.
        """
        return self._period

    def compute(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Compute the EMA and compare latest close to it.

        Args:
            symbol: Ticker symbol of the instrument.
            **kwargs: Must contain ``prices`` -- a pandas DataFrame
                      with a ``close`` column and DatetimeIndex.

        Returns:
            A FactorResult with the EMA value, directional signal,
            and metadata containing the EMA value and latest close.

        Raises:
            No exceptions propagate. Insufficient or invalid data
            returns a neutral result with value=None.
        """
        try:
            return self._compute_impl(symbol, **kwargs)
        except Exception as exc:
            return FactorResult(
                factor_name=f"ema_{self._period}",
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
            FactorResult with computed EMA.

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

        ema_value = float(close.ewm(span=self._period, adjust=False).mean().iloc[-1])
        latest_close = float(close.iloc[-1])
        as_of = close.index[-1].date()

        if latest_close > ema_value:
            signal = Signal.BULLISH
        elif latest_close < ema_value:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        return FactorResult(
            factor_name=f"ema_{self._period}",
            factor_category=self.category,
            symbol=symbol,
            value=ema_value,
            signal=signal,
            as_of=as_of,
            metadata={
                "period": self._period,
                "ema_value": ema_value,
                "latest_close": latest_close,
            },
        )

    def __repr__(self) -> str:
        """Return developer-friendly representation.

        Returns:
            String like EMA(name='ema', category=<FactorCategory.TECHNICAL: 'technical'>).
        """
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, category={self.category!r})"
        )


# Register the EMA factor TYPE in the global registry.
# The period is configurable at instantiation: EMA(period=50).
FactorRegistry.register(EMA)