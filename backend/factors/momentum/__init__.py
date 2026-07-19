"""
Momentum factor implementations.

Implements RSI, MACD, ROC, Williams %R, and Stochastic Oscillator.
All factors inherit from BaseFactor and register with FactorRegistry.
"""

from __future__ import annotations

from datetime import date
from typing import Any, ClassVar

import numpy as np
import pandas as pd

from backend.core.enums import FactorCategory, Signal
from backend.core.factor_result import FactorResult
from backend.factors.base import BaseFactor
from backend.factors.registry import FactorRegistry


class RSI(BaseFactor):
    """Relative Strength Index momentum factor.

    Measures the speed and magnitude of recent price changes to
    evaluate overbought or oversold conditions. Uses Wilder's
    smoothing method (exponential moving average with alpha = 1/period),
    which is the TradingView-compatible calculation.

    Formula::

        RS  = avg_gain / avg_loss
        RSI = 100 - (100 / (1 + RS))

    Signal logic:

    - RSI > 70  -> BEARISH (overbought)
    - RSI < 30  -> BULLISH (oversold)
    - Otherwise -> NEUTRAL

    Args:
        period: Lookback period for gain/loss averaging. Must be >= 1.
                Defaults to 14.

    Required kwargs:

        prices (pd.DataFrame): Must contain a ``close`` column.

    Example::

        >>> rsi = RSI(period=14)
        >>> result = rsi.compute(symbol="RELIANCE", prices=price_df)
        >>> result.value
        55.32
    """

    name: ClassVar[str] = "rsi"
    display_name: ClassVar[str] = "RSI"
    category: ClassVar[FactorCategory] = FactorCategory.MOMENTUM

    def __init__(self, period: int = 14) -> None:
        """Initialize RSI.

        Args:
            period: Lookback period. Must be >= 1.

        Raises:
            ValueError: If period < 1.
        """
        if period < 1:
            raise ValueError(f"RSI period must be >= 1, got {period}")
        self._period: int = period

    @property
    def period(self) -> int:
        """Return the lookback period."""
        return self._period

    def compute(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Compute RSI.

        Args:
            symbol: Ticker symbol.
            **kwargs: Must contain ``prices`` DataFrame.

        Returns:
            FactorResult with RSI value (0-100).
        """
        try:
            return self._compute_impl(symbol, **kwargs)
        except Exception as exc:
            return FactorResult(
                factor_name=f"rsi_{self._period}",
                factor_category=self.category,
                symbol=symbol,
                value=None,
                signal=Signal.NEUTRAL,
                as_of=date.today(),
                metadata={"error": str(exc)},
            )

    def _compute_impl(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Internal RSI computation using Wilder's smoothing."""
        prices = kwargs.get("prices")
        if prices is None:
            raise ValueError("Missing required kwarg: prices")
        if not isinstance(prices, pd.DataFrame):
            raise TypeError(
                f"prices must be a pandas DataFrame, got {type(prices).__name__}"
            )
        if "close" not in prices.columns:
            raise ValueError(
                f"prices DataFrame must contain a 'close' column. Found: {list(prices.columns)}"
            )

        close = prices["close"].dropna()
        min_rows = self._period + 1
        if len(close) < min_rows:
            raise ValueError(
                f"Insufficient data: need {min_rows} closing prices for "
                f"{self._period}-period RSI, got {len(close)}"
            )

        deltas = close.diff().iloc[1:]
        gains = deltas.where(deltas > 0, 0.0)
        losses = (-deltas.where(deltas < 0, 0.0))

        # Wilder's smoothing: EMA with alpha = 1/period
        avg_gain = gains.ewm(alpha=1.0 / self._period, min_periods=self._period, adjust=False).mean()
        avg_loss = losses.ewm(alpha=1.0 / self._period, min_periods=self._period, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi_series = 100.0 - (100.0 / (1.0 + rs))

        rsi_value = float(rsi_series.iloc[-1])
        latest_close = float(close.iloc[-1])
        as_of = close.index[-1].date()

        if rsi_value > 70:
            signal = Signal.BEARISH
        elif rsi_value < 30:
            signal = Signal.BULLISH
        else:
            signal = Signal.NEUTRAL

        return FactorResult(
            factor_name=f"rsi_{self._period}",
            factor_category=self.category,
            symbol=symbol,
            value=rsi_value,
            signal=signal,
            as_of=as_of,
            metadata={
                "period": self._period,
                "rsi": rsi_value,
                "latest_close": latest_close,
            },
        )

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, category={self.category!r})"
        )


FactorRegistry.register(RSI)


class MACD(BaseFactor):
    """Moving Average Convergence Divergence momentum factor.

    Tracks the relationship between two EMAs of closing prices.
    The MACD line is the difference between the fast and slow EMAs.
    The signal line is an EMA of the MACD line. The histogram is
    the difference between MACD and signal.

    Formulas::

        MACD Line   = EMA(close, fast) - EMA(close, slow)
        Signal Line = EMA(MACD Line, signal_period)
        Histogram   = MACD Line - Signal Line

    Signal logic:

    - MACD > Signal  -> BULLISH (bullish crossover)
    - MACD < Signal  -> BEARISH (bearish crossover)
    - MACD == Signal -> NEUTRAL

    Args:
        fast_period: Fast EMA period. Defaults to 12.
        slow_period: Slow EMA period. Defaults to 26.
        signal_period: Signal line EMA period. Defaults to 9.

    Required kwargs:

        prices (pd.DataFrame): Must contain a ``close`` column.

    Example::

        >>> macd = MACD()
        >>> result = macd.compute(symbol="RELIANCE", prices=price_df)
        >>> result.metadata["histogram"]
        1.23
    """

    name: ClassVar[str] = "macd"
    display_name: ClassVar[str] = "MACD"
    category: ClassVar[FactorCategory] = FactorCategory.MOMENTUM

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> None:
        """Initialize MACD.

        Args:
            fast_period: Fast EMA period. Must be >= 1.
            slow_period: Slow EMA period. Must be > fast_period.
            signal_period: Signal line period. Must be >= 1.

        Raises:
            ValueError: If parameters are invalid.
        """
        if fast_period < 1:
            raise ValueError(f"fast_period must be >= 1, got {fast_period}")
        if slow_period <= fast_period:
            raise ValueError(
                f"slow_period ({slow_period}) must be > fast_period ({fast_period})"
            )
        if signal_period < 1:
            raise ValueError(f"signal_period must be >= 1, got {signal_period}")
        self._fast = fast_period
        self._slow = slow_period
        self._signal = signal_period

    @property
    def fast_period(self) -> int:
        """Return the fast EMA period."""
        return self._fast

    @property
    def slow_period(self) -> int:
        """Return the slow EMA period."""
        return self._slow

    @property
    def signal_period(self) -> int:
        """Return the signal line EMA period."""
        return self._signal

    def compute(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Compute MACD.

        Args:
            symbol: Ticker symbol.
            **kwargs: Must contain ``prices`` DataFrame.

        Returns:
            FactorResult with MACD value (MACD line).
        """
        try:
            return self._compute_impl(symbol, **kwargs)
        except Exception as exc:
            return FactorResult(
                factor_name=f"macd_{self._fast}_{self._slow}_{self._signal}",
                factor_category=self.category,
                symbol=symbol,
                value=None,
                signal=Signal.NEUTRAL,
                as_of=date.today(),
                metadata={"error": str(exc)},
            )

    def _compute_impl(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Internal MACD computation."""
        prices = kwargs.get("prices")
        if prices is None:
            raise ValueError("Missing required kwarg: prices")
        if not isinstance(prices, pd.DataFrame):
            raise TypeError(
                f"prices must be a pandas DataFrame, got {type(prices).__name__}"
            )
        if "close" not in prices.columns:
            raise ValueError(
                f"prices DataFrame must contain a 'close' column. Found: {list(prices.columns)}"
            )

        close = prices["close"].dropna()
        min_rows = self._slow + self._signal
        if len(close) < min_rows:
            raise ValueError(
                f"Insufficient data: need {min_rows} closing prices for MACD, "
                f"got {len(close)}"
            )

        ema_fast = close.ewm(span=self._fast, adjust=False).mean()
        ema_slow = close.ewm(span=self._slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self._signal, adjust=False).mean()
        histogram = macd_line - signal_line

        macd_value = float(macd_line.iloc[-1])
        signal_value = float(signal_line.iloc[-1])
        hist_value = float(histogram.iloc[-1])
        latest_close = float(close.iloc[-1])
        as_of = close.index[-1].date()

        if macd_value > signal_value:
            sig = Signal.BULLISH
        elif macd_value < signal_value:
            sig = Signal.BEARISH
        else:
            sig = Signal.NEUTRAL

        return FactorResult(
            factor_name=f"macd_{self._fast}_{self._slow}_{self._signal}",
            factor_category=self.category,
            symbol=symbol,
            value=macd_value,
            signal=sig,
            as_of=as_of,
            metadata={
                "fast_period": self._fast,
                "slow_period": self._slow,
                "signal_period": self._signal,
                "macd": macd_value,
                "signal": signal_value,
                "histogram": hist_value,
                "latest_close": latest_close,
            },
        )

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, category={self.category!r})"
        )


FactorRegistry.register(MACD)


class ROC(BaseFactor):
    """Rate of Change momentum factor.

    Measures the percentage change in closing prices over a
    configurable lookback period.

    Formula::

        ROC = ((close - close_n_periods_ago) / close_n_periods_ago) * 100

    Signal logic:

    - ROC > 0  -> BULLISH (upward momentum)
    - ROC < 0  -> BEARISH (downward momentum)
    - ROC == 0 -> NEUTRAL

    Args:
        period: Number of periods for the change calculation.
                Must be >= 1. Defaults to 12.

    Required kwargs:

        prices (pd.DataFrame): Must contain a ``close`` column.

    Example::

        >>> roc = ROC(period=12)
        >>> result = roc.compute(symbol="RELIANCE", prices=price_df)
        >>> result.value
        3.45
    """

    name: ClassVar[str] = "roc"
    display_name: ClassVar[str] = "ROC"
    category: ClassVar[FactorCategory] = FactorCategory.MOMENTUM

    def __init__(self, period: int = 12) -> None:
        """Initialize ROC.

        Args:
            period: Lookback period. Must be >= 1.

        Raises:
            ValueError: If period < 1.
        """
        if period < 1:
            raise ValueError(f"ROC period must be >= 1, got {period}")
        self._period: int = period

    @property
    def period(self) -> int:
        """Return the lookback period."""
        return self._period

    def compute(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Compute ROC.

        Args:
            symbol: Ticker symbol.
            **kwargs: Must contain ``prices`` DataFrame.

        Returns:
            FactorResult with ROC value (percentage).
        """
        try:
            return self._compute_impl(symbol, **kwargs)
        except Exception as exc:
            return FactorResult(
                factor_name=f"roc_{self._period}",
                factor_category=self.category,
                symbol=symbol,
                value=None,
                signal=Signal.NEUTRAL,
                as_of=date.today(),
                metadata={"error": str(exc)},
            )

    def _compute_impl(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Internal ROC computation."""
        prices = kwargs.get("prices")
        if prices is None:
            raise ValueError("Missing required kwarg: prices")
        if not isinstance(prices, pd.DataFrame):
            raise TypeError(
                f"prices must be a pandas DataFrame, got {type(prices).__name__}"
            )
        if "close" not in prices.columns:
            raise ValueError(
                f"prices DataFrame must contain a 'close' column. Found: {list(prices.columns)}"
            )

        close = prices["close"].dropna()
        if len(close) < self._period + 1:
            raise ValueError(
                f"Insufficient data: need {self._period + 1} closing prices for "
                f"ROC-{self._period}, got {len(close)}"
            )

        current = float(close.iloc[-1])
        previous = float(close.iloc[-(self._period + 1)])

        if previous == 0:
            raise ValueError("Division by zero: previous close is zero")

        roc_value = ((current - previous) / previous) * 100.0
        as_of = close.index[-1].date()

        if roc_value > 0:
            signal = Signal.BULLISH
        elif roc_value < 0:
            signal = Signal.BEARISH
        else:
            signal = Signal.NEUTRAL

        return FactorResult(
            factor_name=f"roc_{self._period}",
            factor_category=self.category,
            symbol=symbol,
            value=roc_value,
            signal=signal,
            as_of=as_of,
            metadata={
                "period": self._period,
                "roc": roc_value,
                "latest_close": current,
                "previous_close": previous,
            },
        )

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, category={self.category!r})"
        )


FactorRegistry.register(ROC)


class WilliamsR(BaseFactor):
    """Williams %R momentum factor.

    Measures overbought and oversold levels by comparing the closing
    price to the high-low range over a configurable period. Outputs
    a value between -100 and 0.

    Formula::

        %R = ((highest_high - close) / (highest_high - lowest_low)) * -100

    Signal logic:

    - %R > -20   -> BEARISH (overbought)
    - %R < -80   -> BULLISH (oversold)
    - Otherwise   -> NEUTRAL

    Args:
        period: Lookback period. Must be >= 1. Defaults to 14.

    Required kwargs:

        prices (pd.DataFrame): Must contain ``high``, ``low``, and
            ``close`` columns.

    Example::

        >>> wr = WilliamsR(period=14)
        >>> result = wr.compute(symbol="RELIANCE", prices=price_df)
        >>> result.value
        -45.0
    """

    name: ClassVar[str] = "williams_r"
    display_name: ClassVar[str] = "Williams %R"
    category: ClassVar[FactorCategory] = FactorCategory.MOMENTUM

    def __init__(self, period: int = 14) -> None:
        """Initialize Williams %R.

        Args:
            period: Lookback period. Must be >= 1.

        Raises:
            ValueError: If period < 1.
        """
        if period < 1:
            raise ValueError(f"Williams %R period must be >= 1, got {period}")
        self._period: int = period

    @property
    def period(self) -> int:
        """Return the lookback period."""
        return self._period

    def compute(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Compute Williams %R.

        Args:
            symbol: Ticker symbol.
            **kwargs: Must contain ``prices`` DataFrame.

        Returns:
            FactorResult with Williams %R value (-100 to 0).
        """
        try:
            return self._compute_impl(symbol, **kwargs)
        except Exception as exc:
            return FactorResult(
                factor_name=f"williams_r_{self._period}",
                factor_category=self.category,
                symbol=symbol,
                value=None,
                signal=Signal.NEUTRAL,
                as_of=date.today(),
                metadata={"error": str(exc)},
            )

    def _compute_impl(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Internal Williams %R computation."""
        prices = kwargs.get("prices")
        if prices is None:
            raise ValueError("Missing required kwarg: prices")
        if not isinstance(prices, pd.DataFrame):
            raise TypeError(
                f"prices must be a pandas DataFrame, got {type(prices).__name__}"
            )

        required_cols = {"high", "low", "close"}
        missing = required_cols - set(prices.columns)
        if missing:
            raise ValueError(
                f"prices DataFrame must contain 'high', 'low', and 'close' columns. "
                f"Missing: {sorted(missing)}. Found: {list(prices.columns)}"
            )

        high = prices["high"].dropna()
        low = prices["low"].dropna()
        close = prices["close"].dropna()

        if len(high) < self._period:
            raise ValueError(
                f"Insufficient data: need {self._period} rows, got {len(high)}"
            )

        # Align on common index
        common_idx = high.index.intersection(low.index).intersection(close.index)
        if len(common_idx) < self._period:
            raise ValueError(
                f"Insufficient aligned data: need {self._period} rows, got {len(common_idx)}"
            )

        h = high.loc[common_idx].tail(self._period)
        l = low.loc[common_idx].tail(self._period)
        c = close.loc[common_idx].tail(self._period)

        highest_high = float(h.max())
        lowest_low = float(l.min())
        latest_close = float(c.iloc[-1])

        rng = highest_high - lowest_low
        if rng == 0:
            wr_value = 0.0
        else:
            wr_value = ((highest_high - latest_close) / rng) * -100.0

        as_of = c.index[-1].date()

        if wr_value > -20:
            signal = Signal.BEARISH
        elif wr_value < -80:
            signal = Signal.BULLISH
        else:
            signal = Signal.NEUTRAL

        return FactorResult(
            factor_name=f"williams_r_{self._period}",
            factor_category=self.category,
            symbol=symbol,
            value=wr_value,
            signal=signal,
            as_of=as_of,
            metadata={
                "period": self._period,
                "williams_r": wr_value,
                "highest_high": highest_high,
                "lowest_low": lowest_low,
                "latest_close": latest_close,
            },
        )

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, category={self.category!r})"
        )


FactorRegistry.register(WilliamsR)


class StochasticOscillator(BaseFactor):
    """Stochastic Oscillator momentum factor.

    Compares a closing price to its price range over a configurable
    period. Outputs %K (fast) and %D (smoothed %K).

    Formulas::

        %K = ((close - lowest_low) / (highest_high - lowest_low)) * 100
        %D = SMA(%K, smooth)

    Signal logic:

    - %K > 80  -> BEARISH (overbought)
    - %K < 20  -> BULLISH (oversold)
    - Otherwise -> NEUTRAL

    Args:
        k_period: %K lookback period. Must be >= 1. Defaults to 14.
        d_period: %D smoothing period (not used in computation, kept for
                  metadata). Defaults to 3.
        smooth: Smoothing period for %D. Must be >= 1. Defaults to 3.

    Required kwargs:

        prices (pd.DataFrame): Must contain ``high``, ``low``, and
            ``close`` columns.

    Example::

        >>> stoch = StochasticOscillator()
        >>> result = stoch.compute(symbol="RELIANCE", prices=price_df)
        >>> result.metadata["percent_k"]
        65.0
        >>> result.metadata["percent_d"]
        58.5
    """

    name: ClassVar[str] = "stochastic"
    display_name: ClassVar[str] = "Stochastic Oscillator"
    category: ClassVar[FactorCategory] = FactorCategory.MOMENTUM

    def __init__(
        self,
        k_period: int = 14,
        d_period: int = 3,
        smooth: int = 3,
    ) -> None:
        """Initialize Stochastic Oscillator.

        Args:
            k_period: %K lookback period. Must be >= 1.
            d_period: %D period (metadata). Must be >= 1.
            smooth: Smoothing period for %D. Must be >= 1.

        Raises:
            ValueError: If any parameter < 1.
        """
        if k_period < 1:
            raise ValueError(f"k_period must be >= 1, got {k_period}")
        if d_period < 1:
            raise ValueError(f"d_period must be >= 1, got {d_period}")
        if smooth < 1:
            raise ValueError(f"smooth must be >= 1, got {smooth}")
        self._k_period = k_period
        self._d_period = d_period
        self._smooth = smooth

    @property
    def k_period(self) -> int:
        """Return the %K lookback period."""
        return self._k_period

    @property
    def d_period(self) -> int:
        """Return the %D period."""
        return self._d_period

    @property
    def smooth(self) -> int:
        """Return the smoothing period."""
        return self._smooth

    def compute(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Compute Stochastic Oscillator.

        Args:
            symbol: Ticker symbol.
            **kwargs: Must contain ``prices`` DataFrame.

        Returns:
            FactorResult with %K value (0-100).
        """
        try:
            return self._compute_impl(symbol, **kwargs)
        except Exception as exc:
            return FactorResult(
                factor_name=f"stochastic_{self._k_period}_{self._smooth}",
                factor_category=self.category,
                symbol=symbol,
                value=None,
                signal=Signal.NEUTRAL,
                as_of=date.today(),
                metadata={"error": str(exc)},
            )

    def _compute_impl(self, symbol: str, **kwargs: Any) -> FactorResult:
        """Internal Stochastic Oscillator computation."""
        prices = kwargs.get("prices")
        if prices is None:
            raise ValueError("Missing required kwarg: prices")
        if not isinstance(prices, pd.DataFrame):
            raise TypeError(
                f"prices must be a pandas DataFrame, got {type(prices).__name__}"
            )

        required_cols = {"high", "low", "close"}
        missing = required_cols - set(prices.columns)
        if missing:
            raise ValueError(
                f"prices DataFrame must contain 'high', 'low', and 'close' columns. "
                f"Missing: {sorted(missing)}. Found: {list(prices.columns)}"
            )

        high = prices["high"].dropna()
        low = prices["low"].dropna()
        close = prices["close"].dropna()

        min_rows = self._k_period + self._smooth
        if len(high) < min_rows:
            raise ValueError(
                f"Insufficient data: need {min_rows} rows for Stochastic, "
                f"got {len(high)}"
            )

        common_idx = high.index.intersection(low.index).intersection(close.index)
        if len(common_idx) < min_rows:
            raise ValueError(
                f"Insufficient aligned data: need {min_rows} rows, got {len(common_idx)}"
            )

        h = high.loc[common_idx]
        l = low.loc[common_idx]
        c = close.loc[common_idx]

        # Rolling highest high and lowest low
        highest = h.rolling(window=self._k_period).max()
        lowest = l.rolling(window=self._k_period).min()

        rng = highest - lowest
        # Avoid division by zero
        rng = rng.replace(0, np.nan)
        raw_k = ((c - lowest) / rng) * 100.0

        # %D is SMA of %K
        percent_d = raw_k.rolling(window=self._smooth).mean()

        # Get latest valid values
        valid_k = raw_k.dropna()
        valid_d = percent_d.dropna()

        if len(valid_k) == 0:
            raise ValueError("No valid %K values computed")

        percent_k = float(valid_k.iloc[-1])
        percent_d_val = float(valid_d.iloc[-1]) if len(valid_d) > 0 else percent_k
        latest_close = float(c.iloc[-1])
        as_of = c.index[-1].date()

        if percent_k > 80:
            signal = Signal.BEARISH
        elif percent_k < 20:
            signal = Signal.BULLISH
        else:
            signal = Signal.NEUTRAL

        return FactorResult(
            factor_name=f"stochastic_{self._k_period}_{self._smooth}",
            factor_category=self.category,
            symbol=symbol,
            value=percent_k,
            signal=signal,
            as_of=as_of,
            metadata={
                "k_period": self._k_period,
                "d_period": self._d_period,
                "smooth": self._smooth,
                "percent_k": percent_k,
                "percent_d": percent_d_val,
                "latest_close": latest_close,
            },
        )

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, category={self.category!r})"
        )


FactorRegistry.register(StochasticOscillator)