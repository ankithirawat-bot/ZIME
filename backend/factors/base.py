"""
Abstract base class for all quantitative factors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from backend.core.enums import FactorCategory
from backend.core.factor_result import FactorResult


class BaseFactor(ABC):
    """Abstract base class that every factor must inherit from.

    A factor is a stateless, single-purpose computation that analyzes
    an instrument and returns a standardized FactorResult.
    Factors are registered with the FactorRegistry and
    discovered at runtime by the scoring and engine layers.

    Subclasses must define the following class attributes:

        name (str):         Unique machine-readable identifier
                            (e.g. "sma_20", "roe_ttm").
        display_name (str): Human-readable label
                            (e.g. "SMA 20", "Return on Equity (TTM)").
        category:           One of the FactorCategory enum values.

    Subclasses must implement the compute() method.

    Example::

        class SMA20(BaseFactor):
            name = "sma_20"
            display_name = "SMA 20"
            category = FactorCategory.TECHNICAL

            def compute(self, symbol: str, **kwargs) -> FactorResult:
                prices = kwargs["prices"]
                # ... computation logic ...
                return FactorResult(...)
    """

    name: ClassVar[str]
    display_name: ClassVar[str]
    category: ClassVar[FactorCategory]

    @abstractmethod
    def compute(self, symbol: str, **kwargs) -> FactorResult:
        """Compute the factor for a single instrument.

        Args:
            symbol:  Ticker symbol of the instrument to analyze.
            **kwargs: Factor-specific inputs. Concrete subclasses should
                      document their required kwargs. Common patterns:

                      - prices: A price DataFrame (for technical factors).
                      - financials: Financial statement data (for
                        fundamental factors).
                      - returns: A return series (for risk factors).

        Returns:
            A FactorResult containing the computed value,
            directional signal, and metadata.

        Raises:
            No exceptions should propagate from factor computation.
            If data is missing or insufficient, return a FactorResult
            with value=None and signal=Signal.NEUTRAL.
        """
        ...

    def __repr__(self) -> str:
        """Return a developer-friendly string representation.

        Returns:
            A string in the format ClassName(name=..., category=...).
        """
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name!r}, category={self.category!r})"
        )
