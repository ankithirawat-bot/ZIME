"""
Instrument Mapper.

Maps standard ticker symbols to Upstox instrument keys.
"""

from __future__ import annotations


class InstrumentMapper:
    """Maps ticker symbols to Upstox instrument keys.

    Supports NSE equities.  Future expansion for BSE, indices, ETFs.
    """

    # Static mapping of known symbols to Upstox instrument keys.
    # Keys are lowercase for case-insensitive lookup.
    _NSE_MAP: dict[str, str] = {
        "reliance": "RELIANCE",
        "tcs": "TCS",
        "hdfcbank": "HDFCBANK",
        "infy": "INFY",
        "infosys": "INFY",
        "icicibank": "ICICIBANK",
        "hindunilvr": "HINDUNILVR",
        "itc": "ITC",
        "sbin": "SBIN",
        "bhartiairtel": "BHARTIARTL",
        "kotakbank": "KOTAKBANK",
        "lt": "LT",
        "asia-paints": "ASIANPAINT",
        "asianpaint": "ASIANPAINT",
        "axisbank": "AXISBANK",
        "maruti": "MARUTI",
        "titan": "TITAN",
        "sunpharma": "SUNPHARMA",
        "tatasteel": "TATASTEEL",
        "wipro": "WIPRO",
        "bajajfinance": "BAJFINANCE",
        "hcltech": "HCLTECH",
        "tech-mahindra": "TECHM",
        "techmahindra": "TECHM",
        "nestleind": "NESTLEIND",
        "ultracemco": "ULTRACEMCO",
        "tata-motors": "TATAMOTORS",
        "tatamotors": "TATAMOTORS",
    }

    def resolve(self, symbol: str) -> str | None:
        """Resolve a ticker symbol to an Upstox instrument key.

        Args:
            symbol: Ticker symbol (e.g. "RELIANCE").

        Returns:
            Upstox instrument key or None if not found.
        """
        return self._NSE_MAP.get(symbol.lower())

    def exchange_segment(self, exchange: str) -> str:
        """Convert exchange identifier to Upstox segment.

        Args:
            exchange: Exchange identifier (e.g. "NSE", "BSE").

        Returns:
            Upstox exchange segment (e.g. "NSE_EQ").
        """
        mapping = {
            "NSE": "NSE_EQ",
            "BSE": "BSE_EQ",
        }
        return mapping.get(exchange.upper(), "NSE_EQ")

    def supported_symbols(self) -> tuple[str, ...]:
        """Return all mapped symbols (Upstox format).

        Returns:
            Tuple of instrument keys.
        """
        return tuple(sorted(set(self._NSE_MAP.values())))

    def has_symbol(self, symbol: str) -> bool:
        """Check if a symbol is mappable.

        Args:
            symbol: Ticker symbol.

        Returns:
            True if mappable.
        """
        return symbol.lower() in self._NSE_MAP
