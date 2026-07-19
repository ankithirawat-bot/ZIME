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

class WMA(BaseFactor):
    """Weighted Moving Average price factor.

    Computes a weighted average of closing prices where recent prices
    receive higher linear weights. The weights form an arithmetic
    progression: [1, 2, ..., period].

    Formula::

        WMA = (price[0]*1 + price[1]*2 + ... + price[n]*n) / (1 + 2 + ... + n)

    The signal is derived by comparing the latest closing price to the
    WMA value:

    - Close > WMA  -> BULLISH
    - Close < WMA  -> BEARISH
    - Close == WMA -> NEUTRAL

    The factor type is registered in the FactorRegistry under the name
    ``"wma"``. The period is configurable at instantiation time.

    Args:
        period: Number of trading days in the lookback window. Must be
                a positive integer. Defaults to 20.

    Required kwargs for compute():

        prices (pd.DataFrame): Historical price data with at minimum
            a ``close`` column and a DatetimeIndex. The DataFrame must
            contain at least ``period`` rows of non-NaN closing prices.

    Example::

        >>> wma = WMA(period=20)
        >>> result = wma.compute(symbol="RELIANCE", prices=price_df)
        >>> result.value
        2457.50
        >>> result.signal
        <Signal.BULLISH: 'bullish'>

        # Discover via registry
        >>> from backend.factors.registry import FactorRegistry
        >>> FactorRegistry.get("wma")
        <class 'backend.factors.price.WMA'>
    """

    name: ClassVar[str] = "wma"
    display_name: ClassVar[str] = "WMA"
    category: ClassVar[FactorCategory] = FactorCategory.TECHNICAL

    def __init__(self, period: int = 20) -> None:
        """Initialize WMA with a configurable lookback period.

        Args:
            period: Number of trading days. Must be >= 1.

        Raises:
            ValueError: If period is less than 1.
        """
        if period < 1:
            raise ValueError(
                f"WMA period must be >= 1, got {period}"
            )
        self._period: int = period

    @property
    def period(self) -> int:
        """Return the lookback period.

        Returns:
            The number of trading days used in the weighted average.
        """
        return self._period

    def compute(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Compute the WMA and compare latest close to it.

        Args:
            symbol: Ticker symbol of the instrument.
            **kwargs: Must contain ``prices`` -- a pandas DataFrame
                      with a ``close`` column and DatetimeIndex.

        Returns:
            A FactorResult with the WMA value, directional signal,
            and metadata containing the WMA value and latest close.

        Raises:
            No exceptions propagate. Insufficient or invalid data
            returns a neutral result with value=None.
        """
        try:
            return self._compute_impl(symbol, **kwargs)
        except Exception as exc:
            return FactorResult(
                factor_name=f"wma_{self._period}",
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
            FactorResult with computed WMA.

        Raises:
            ValueError: If prices is missing, wrong type, or has
                        insufficient data.
        """
        import numpy as np

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

        window = close.tail(self._period).values
        weights = np.arange(1, self._period + 1, dtype=float)
        wma_value = float(np.dot(window, weights) / weights.sum())
        latest_close = float(close.iloc[-1])
        as_of = close.index[-1].date()

        if latest_close > wma_value:
            signal = Signal.BULLISH
        elif latest_close < wma_value:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        return FactorResult(
            factor_name=f"wma_{self._period}",
            factor_category=self.category,
            symbol=symbol,
            value=wma_value,
            signal=signal,
            as_of=as_of,
            metadata={
                "period": self._period,
                "wma_value": wma_value,
                "latest_close": latest_close,
            },
        )

    def __repr__(self) -> str:
        """Return developer-friendly representation.

        Returns:
            String like WMA(name='wma', category=<FactorCategory.TECHNICAL: 'technical'>).
        """
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, category={self.category!r})"
        )


# Register the WMA factor TYPE in the global registry.
# The period is configurable at instantiation: WMA(period=50).
FactorRegistry.register(WMA)

class VWMA(BaseFactor):
    """Volume Weighted Moving Average price factor.

    Computes a moving average weighted by volume over a configurable
    lookback window. Higher-volume days have greater influence on the
    average, making VWMA more representative of true transaction price
    than a simple moving average.

    Formula::

        VWMA = sum(Close * Volume) / sum(Volume)

    The signal is derived by comparing the latest closing price to the
    VWMA value:

    - Close > VWMA  -> BULLISH
    - Close < VWMA  -> BEARISH
    - Close == VWMA -> NEUTRAL

    The factor type is registered in the FactorRegistry under the name
    ``"vwma"``. The period is configurable at instantiation time.

    Args:
        period: Number of trading days in the lookback window. Must be
                a positive integer. Defaults to 20.

    Required kwargs for compute():

        prices (pd.DataFrame): Historical price data with at minimum
            a ``close`` column and a ``volume`` column, indexed by date.
            The DataFrame must contain at least ``period`` rows of
            valid (non-NaN) closing prices and volumes.

    Example::

        >>> vwma = VWMA(period=20)
        >>> result = vwma.compute(symbol="RELIANCE", prices=price_df)
        >>> result.value
        2455.90
        >>> result.signal
        <Signal.BULLISH: 'bullish'>

        # Discover via registry
        >>> from backend.factors.registry import FactorRegistry
        >>> FactorRegistry.get("vwma")
        <class 'backend.factors.price.VWMA'>
    """

    name: ClassVar[str] = "vwma"
    display_name: ClassVar[str] = "VWMA"
    category: ClassVar[FactorCategory] = FactorCategory.TECHNICAL

    def __init__(self, period: int = 20) -> None:
        """Initialize VWMA with a configurable lookback period.

        Args:
            period: Number of trading days. Must be >= 1.

        Raises:
            ValueError: If period is less than 1.
        """
        if period < 1:
            raise ValueError(
                f"VWMA period must be >= 1, got {period}"
            )
        self._period: int = period

    @property
    def period(self) -> int:
        """Return the lookback period.

        Returns:
            The number of trading days used in the volume weighted average.
        """
        return self._period

    def compute(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Compute the VWMA and compare latest close to it.

        Args:
            symbol: Ticker symbol of the instrument.
            **kwargs: Must contain ``prices`` -- a pandas DataFrame
                      with ``close`` and ``volume`` columns and a
                      DatetimeIndex.

        Returns:
            A FactorResult with the VWMA value, directional signal,
            and metadata containing the VWMA value and latest close.

        Raises:
            No exceptions propagate. Insufficient or invalid data
            returns a neutral result with value=None.
        """
        try:
            return self._compute_impl(symbol, **kwargs)
        except Exception as exc:
            return FactorResult(
                factor_name=f"vwma_{self._period}",
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
            **kwargs: Must contain ``prices`` DataFrame with close and
                      volume columns.

        Returns:
            FactorResult with computed VWMA.

        Raises:
            ValueError: If prices is missing, wrong type, missing
                        columns, insufficient data, or zero total volume.
        """
        import numpy as np

        prices = kwargs.get("prices")
        if prices is None:
            raise ValueError("Missing required kwarg: prices")

        if not isinstance(prices, pd.DataFrame):
            raise TypeError(
                f"prices must be a pandas DataFrame, "
                f"got {type(prices).__name__}"
            )

        required_cols = {"close", "volume"}
        missing = required_cols - set(prices.columns)
        if missing:
            raise ValueError(
                f"prices DataFrame must contain 'close' and 'volume' columns. "
                f"Missing: {sorted(missing)}. "
                f"Found: {list(prices.columns)}"
            )

        close = prices["close"].dropna()
        volume = prices["volume"].dropna()

        if len(close) < self._period:
            raise ValueError(
                f"Insufficient data: need {self._period} closing prices, "
                f"got {len(close)}"
            )

        if len(volume) < self._period:
            raise ValueError(
                f"Insufficient data: need {self._period} volume values, "
                f"got {len(volume)}"
            )

        # Align close and volume on their common index
        common_idx = close.index.intersection(volume.index)
        if len(common_idx) < self._period:
            raise ValueError(
                f"Insufficient aligned data: need {self._period} rows with "
                f"both close and volume, got {len(common_idx)}"
            )

        close_aligned = close.loc[common_idx].tail(self._period)
        volume_aligned = volume.loc[common_idx].tail(self._period)

        total_volume = float(volume_aligned.sum())
        if total_volume <= 0:
            raise ValueError(
                f"Total volume over {self._period} period window is "
                f"zero or negative ({total_volume})"
            )

        vwma_value = float(
            np.dot(close_aligned.values, volume_aligned.values) / total_volume
        )
        latest_close = float(close.iloc[-1])
        as_of = close.index[-1].date()

        if latest_close > vwma_value:
            signal = Signal.BULLISH
        elif latest_close < vwma_value:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        return FactorResult(
            factor_name=f"vwma_{self._period}",
            factor_category=self.category,
            symbol=symbol,
            value=vwma_value,
            signal=signal,
            as_of=as_of,
            metadata={
                "period": self._period,
                "vwma_value": vwma_value,
                "latest_close": latest_close,
                "total_volume": total_volume,
            },
        )

    def __repr__(self) -> str:
        """Return developer-friendly representation.

        Returns:
            String like VWMA(name='vwma', category=<FactorCategory.TECHNICAL: 'technical'>).
        """
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, category={self.category!r})"
        )


# Register the VWMA factor TYPE in the global registry.
# The period is configurable at instantiation: VWMA(period=50).
FactorRegistry.register(VWMA)

class ATR(BaseFactor):
    """Average True Range volatility factor.

    Measures market volatility by computing the average of the True
    Range over a configurable lookback window. ATR is a non-directional
    indicator — it measures the magnitude of price movement regardless
    of direction.

    True Range (TR) for each bar::

        TR = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )

    ATR is the Simple Moving Average of TR over the configured period.

    Signal logic (volatility-based):

    - Latest TR > ATR  -> BULLISH (expanding volatility, opportunity)
    - Latest TR < ATR  -> BEARISH (contracting volatility, caution)
    - Latest TR == ATR -> NEUTRAL

    The factor type is registered in the FactorRegistry under the name
    ``"atr"``. The period is configurable at instantiation time.

    Args:
        period: Number of trading days for the ATR calculation.
                Must be a positive integer. Defaults to 14.

    Required kwargs for compute():

        prices (pd.DataFrame): Historical price data with ``high``,
            ``low``, and ``close`` columns, indexed by date. Must
            contain at least ``period + 1`` rows (one extra for
            the first prev_close).

    Example::

        >>> atr = ATR(period=14)
        >>> result = atr.compute(symbol="RELIANCE", prices=price_df)
        >>> result.value
        45.23
        >>> result.metadata["atr"]
        45.23

        # Discover via registry
        >>> from backend.factors.registry import FactorRegistry
        >>> FactorRegistry.get("atr")
        <class 'backend.factors.price.ATR'>
    """

    name: ClassVar[str] = "atr"
    display_name: ClassVar[str] = "ATR"
    category: ClassVar[FactorCategory] = FactorCategory.TECHNICAL

    def __init__(self, period: int = 14) -> None:
        """Initialize ATR with a configurable lookback period.

        Args:
            period: Number of trading days. Must be >= 1.

        Raises:
            ValueError: If period is less than 1.
        """
        if period < 1:
            raise ValueError(
                f"ATR period must be >= 1, got {period}"
            )
        self._period: int = period

    @property
    def period(self) -> int:
        """Return the lookback period.

        Returns:
            The number of trading days used in the ATR calculation.
        """
        return self._period

    def compute(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Compute the ATR.

        Args:
            symbol: Ticker symbol of the instrument.
            **kwargs: Must contain ``prices`` -- a pandas DataFrame
                      with ``high``, ``low``, and ``close`` columns.

        Returns:
            A FactorResult with the ATR value and metadata.

        Raises:
            No exceptions propagate. Invalid data returns a neutral
            result with value=None.
        """
        try:
            return self._compute_impl(symbol, **kwargs)
        except Exception as exc:
            return FactorResult(
                factor_name=f"atr_{self._period}",
                factor_category=self.category,
                symbol=symbol,
                value=None,
                signal=Signal.NEUTRAL,
                as_of=date.today(),
                metadata={"error": str(exc)},
            )

    def _compute_impl(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Internal computation.

        Args:
            symbol: Ticker symbol.
            **kwargs: Must contain ``prices`` DataFrame.

        Returns:
            FactorResult with computed ATR.

        Raises:
            ValueError: If prices is missing, wrong type, missing
                        columns, or insufficient data.
        """
        import numpy as np

        prices = kwargs.get("prices")
        if prices is None:
            raise ValueError("Missing required kwarg: prices")

        if not isinstance(prices, pd.DataFrame):
            raise TypeError(
                f"prices must be a pandas DataFrame, "
                f"got {type(prices).__name__}"
            )

        required_cols = {"high", "low", "close"}
        missing = required_cols - set(prices.columns)
        if missing:
            raise ValueError(
                f"prices DataFrame must contain 'high', 'low', and 'close' columns. "
                f"Missing: {sorted(missing)}. "
                f"Found: {list(prices.columns)}"
            )

        high = prices["high"].dropna()
        low = prices["low"].dropna()
        close = prices["close"].dropna()

        # Need period + 1 rows because first TR needs prev_close
        min_rows = self._period + 1
        if len(high) < min_rows:
            raise ValueError(
                f"Insufficient data: need {min_rows} rows for {self._period}-period ATR, "
                f"got {len(high)}"
            )
        if len(low) < min_rows:
            raise ValueError(
                f"Insufficient data: need {min_rows} rows, "
                f"got {len(low)} low values"
            )
        if len(close) < min_rows:
            raise ValueError(
                f"Insufficient data: need {min_rows} rows, "
                f"got {len(close)} close values"
            )

        # Align on common index
        common_idx = high.index.intersection(low.index).intersection(close.index)
        if len(common_idx) < min_rows:
            raise ValueError(
                f"Insufficient aligned data: need {min_rows} rows with "
                f"high, low, and close, got {len(common_idx)}"
            )

        h = high.loc[common_idx]
        l = low.loc[common_idx]
        c = close.loc[common_idx]

        prev_close = c.shift(1)
        tr1 = h - l
        tr2 = (h - prev_close).abs()
        tr3 = (l - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Drop first row (NaN from prev_close) then take last period
        tr = tr.iloc[1:]
        if len(tr) < self._period:
            raise ValueError(
                f"Insufficient True Range data: need {self._period}, got {len(tr)}"
            )

        tr_window = tr.tail(self._period)
        atr_value = float(tr_window.mean())
        latest_tr = float(tr.iloc[-1])
        latest_close = float(c.iloc[-1])
        as_of = c.index[-1].date()

        # ATR is non-directional; signal based on TR vs ATR
        if latest_tr > atr_value:
            signal = Signal.BULLISH
        elif latest_tr < atr_value:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        return FactorResult(
            factor_name=f"atr_{self._period}",
            factor_category=self.category,
            symbol=symbol,
            value=atr_value,
            signal=signal,
            as_of=as_of,
            metadata={
                "period": self._period,
                "atr": atr_value,
                "latest_tr": latest_tr,
                "latest_close": latest_close,
                "calculation_method": "SMA",
            },
        )

    def __repr__(self) -> str:
        """Return developer-friendly representation.

        Returns:
            String like ATR(name='atr', category=<FactorCategory.TECHNICAL: 'technical'>).
        """
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, category={self.category!r})"
        )


# Register the ATR factor TYPE in the global registry.
# The period is configurable at instantiation: ATR(period=21).
FactorRegistry.register(ATR)


class BollingerBands(BaseFactor):
    """Bollinger Bands volatility envelope factor.

    Computes a volatility envelope around a simple moving average.
    The bands expand when volatility increases and contract when
    volatility decreases, providing a dynamic support/resistance
    framework.

    Formulas::

        Middle Band = SMA(close, period)
        Upper Band  = Middle + (std_multiplier * StdDev(close, period))
        Lower Band  = Middle - (std_multiplier * StdDev(close, period))
        Bandwidth   = (Upper - Lower) / Middle
        Percent B   = (Close - Lower) / (Upper - Lower)

    Signal logic:

    - Close > Upper Band  -> BEARISH (overbought)
    - Close < Lower Band  -> BULLISH (oversold)
    - Otherwise           -> NEUTRAL

    The factor type is registered in the FactorRegistry under the name
    ``"bollinger_bands"``.

    Args:
        period: Number of trading days for the SMA and standard
                deviation. Must be a positive integer. Defaults to 20.
        std_multiplier: Number of standard deviations for the bands.
                        Must be positive. Defaults to 2.0.

    Required kwargs for compute():

        prices (pd.DataFrame): Historical price data with a ``close``
            column, indexed by date. Must contain at least ``period``
            rows of non-NaN closing prices.

    Example::

        >>> bb = BollingerBands(period=20, std_multiplier=2.0)
        >>> result = bb.compute(symbol="RELIANCE", prices=price_df)
        >>> result.metadata["bandwidth"]
        0.045
        >>> result.metadata["percent_b"]
        0.65

        # Discover via registry
        >>> from backend.factors.registry import FactorRegistry
        >>> FactorRegistry.get("bollinger_bands")
        <class 'backend.factors.price.BollingerBands'>
    """

    name: ClassVar[str] = "bollinger_bands"
    display_name: ClassVar[str] = "Bollinger Bands"
    category: ClassVar[FactorCategory] = FactorCategory.TECHNICAL

    def __init__(self, period: int = 20, std_multiplier: float = 2.0) -> None:
        """Initialize Bollinger Bands with period and std multiplier.

        Args:
            period: Number of trading days. Must be >= 1.
            std_multiplier: Standard deviation multiplier. Must be > 0.

        Raises:
            ValueError: If period < 1 or std_multiplier <= 0.
        """
        if period < 1:
            raise ValueError(
                f"Bollinger Bands period must be >= 1, got {period}"
            )
        if std_multiplier <= 0:
            raise ValueError(
                f"Bollinger Bands std_multiplier must be > 0, got {std_multiplier}"
            )
        self._period: int = period
        self._std_multiplier: float = std_multiplier

    @property
    def period(self) -> int:
        """Return the lookback period.

        Returns:
            The number of trading days used in the SMA and StdDev.
        """
        return self._period

    @property
    def std_multiplier(self) -> float:
        """Return the standard deviation multiplier.

        Returns:
            The multiplier applied to the standard deviation.
        """
        return self._std_multiplier

    def compute(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Compute the Bollinger Bands.

        Args:
            symbol: Ticker symbol of the instrument.
            **kwargs: Must contain ``prices`` -- a pandas DataFrame
                      with a ``close`` column.

        Returns:
            A FactorResult with the middle band value and metadata
            containing all band values.

        Raises:
            No exceptions propagate. Invalid data returns a neutral
            result with value=None.
        """
        try:
            return self._compute_impl(symbol, **kwargs)
        except Exception as exc:
            return FactorResult(
                factor_name=f"bollinger_bands_{self._period}",
                factor_category=self.category,
                symbol=symbol,
                value=None,
                signal=Signal.NEUTRAL,
                as_of=date.today(),
                metadata={"error": str(exc)},
            )

    def _compute_impl(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Internal computation.

        Args:
            symbol: Ticker symbol.
            **kwargs: Must contain ``prices`` DataFrame.

        Returns:
            FactorResult with computed Bollinger Bands.

        Raises:
            ValueError: If prices is missing, wrong type, missing
                        close column, or insufficient data.
        """
        import numpy as np

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

        window = close.tail(self._period)
        middle = float(window.mean())
        std = float(window.std(ddof=0))

        upper = middle + (self._std_multiplier * std)
        lower = middle - (self._std_multiplier * std)
        bandwidth = (upper - lower) / middle if middle != 0 else 0.0
        latest_close = float(close.iloc[-1])
        percent_b = (
            (latest_close - lower) / (upper - lower)
            if (upper - lower) != 0
            else 0.5
        )
        as_of = close.index[-1].date()

        if latest_close > upper:
            signal = Signal.BEARISH
        elif latest_close < lower:
            signal = Signal.BULLISH
        else:
            signal = Signal.NEUTRAL

        return FactorResult(
            factor_name=f"bollinger_bands_{self._period}",
            factor_category=self.category,
            symbol=symbol,
            value=middle,
            signal=signal,
            as_of=as_of,
            metadata={
                "period": self._period,
                "std_multiplier": self._std_multiplier,
                "middle_band": middle,
                "upper_band": upper,
                "lower_band": lower,
                "bandwidth": bandwidth,
                "percent_b": percent_b,
                "latest_close": latest_close,
            },
        )

    def __repr__(self) -> str:
        """Return developer-friendly representation.

        Returns:
            String like BollingerBands(name='bollinger_bands', ...).
        """
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, category={self.category!r})"
        )


# Register the BollingerBands factor TYPE in the global registry.
FactorRegistry.register(BollingerBands)