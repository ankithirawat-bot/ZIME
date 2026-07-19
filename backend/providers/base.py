"""
Market Data Provider Interface.

Abstract base class for market data providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class MarketDataProvider(ABC):
    """Abstract interface for market data providers.

    All providers must implement ``get_history()`` which returns
    a DataFrame with OHLCV columns.

    The provider is responsible for:
    - Connecting to the data source
    - Downloading historical data
    - Returning a standardized DataFrame

    The caller (ResearchService) handles:
    - Column validation
    - Column normalization
    - Error handling
    """

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        period: str,
        interval: str,
    ) -> pd.DataFrame | None:
        """Download historical OHLCV data.

        Args:
            symbol:   Ticker symbol (e.g. "RELIANCE.NS").
            period:   Historical period (e.g. "1y").
            interval: Data interval (e.g. "1d").

        Returns:
            A DataFrame with OHLCV columns, or None on failure.

        Raises:
            Exception: If the download fails (caller handles).
        """
