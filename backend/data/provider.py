"""
Market Data Provider abstraction.

Abstract base class that all data providers must implement.
Enables dependency inversion: the engine depends on the interface,
not on concrete providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.data.models import DataRequest, DataResponse, DataType


class MarketDataProvider(ABC):
    """Abstract interface for market data providers.

    Subclasses implement ``fetch`` for each supported ``DataType``.
    The registry uses ``supports`` and ``provider_name`` for routing.
    """

    @abstractmethod
    def supports(self, data_type: DataType) -> bool:
        """Return True if this provider can supply *data_type*.

        Args:
            data_type: The data type to check.

        Returns:
            True when the data type is supported.
        """

    @abstractmethod
    def fetch(self, request: DataRequest) -> DataResponse:
        """Fetch data for the given request.

        Args:
            request: Validated data request.

        Returns:
            DataResponse with payload or error status.
        """

    @abstractmethod
    def validate(self, request: DataRequest) -> bool:
        """Pre-flight validation of a request before fetching.

        Args:
            request: The request to validate.

        Returns:
            True when the request is structurally valid for this provider.
        """

    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider."""

    @abstractmethod
    def version(self) -> str:
        """Semantic version of this provider implementation."""
