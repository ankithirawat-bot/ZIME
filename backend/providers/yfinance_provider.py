"""
YFinance Market Data Provider.

Implements the MarketDataProvider interface using yfinance.
"""

from __future__ import annotations

import pandas as pd

from backend.providers.base import MarketDataProvider


class YFinanceProvider(MarketDataProvider):
    """Market data provider using yfinance.

    Downloads historical OHLCV data from Yahoo Finance.

    Usage::

        provider = YFinanceProvider()
        data = provider.get_history("RELIANCE.NS", "1y", "1d")
    """

    def get_history(
        self,
        symbol: str,
        period: str,
        interval: str,
    ) -> pd.DataFrame | None:
        """Download historical OHLCV data from Yahoo Finance.

        Args:
            symbol:   Ticker symbol.
            period:   Historical period.
            interval: Data interval.

        Returns:
            A DataFrame with OHLCV columns, or None on failure.

        Raises:
            Exception: If the download fails (caller handles).
        """
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)
        return data
