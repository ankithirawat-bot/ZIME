"""
Provider Registry.

Maps DataType to provider implementations.  No if/elif dispatch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.data.exceptions import UnsupportedDataTypeError, UnsupportedProviderError
from backend.data.models import DataType

if TYPE_CHECKING:
    from backend.data.provider import MarketDataProvider


class ProviderRegistry:
    """Registry mapping DataType to MarketDataProvider instances.

    Providers register which data types they support.  The engine
    resolves the correct provider through this registry.
    """

    def __init__(self) -> None:
        self._providers: dict[str, MarketDataProvider] = {}
        self._type_map: dict[DataType, str] = {}

    def register(self, provider: MarketDataProvider, data_types: tuple[DataType, ...]) -> None:
        """Register a provider for one or more data types.

        Args:
            provider:   Provider instance.
            data_types: Data types this provider supports.
        """
        name = provider.provider_name()
        self._providers[name] = provider
        for dt in data_types:
            self._type_map[dt] = name

    def resolve(self, data_type: DataType) -> MarketDataProvider:
        """Resolve the provider for a data type.

        Args:
            data_type: Data type to resolve.

        Returns:
            Provider instance.

        Raises:
            UnsupportedDataTypeError: If no provider is registered.
        """
        name = self._type_map.get(data_type)
        if name is None:
            raise UnsupportedDataTypeError(data_type.value, "none")
        return self._providers[name]

    def resolve_by_name(self, provider_name: str) -> MarketDataProvider:
        """Resolve a provider by name.

        Args:
            provider_name: Provider name.

        Returns:
            Provider instance.

        Raises:
            UnsupportedProviderError: If provider is not registered.
        """
        provider = self._providers.get(provider_name)
        if provider is None:
            raise UnsupportedProviderError(provider_name)
        return provider

    def supported_types(self, provider_name: str) -> tuple[DataType, ...]:
        """Return data types supported by a provider.

        Args:
            provider_name: Provider name.

        Returns:
            Tuple of supported data types.

        Raises:
            UnsupportedProviderError: If provider is not registered.
        """
        if provider_name not in self._providers:
            raise UnsupportedProviderError(provider_name)
        return tuple(
            dt for dt, name in self._type_map.items() if name == provider_name
        )

    def available_providers(self) -> tuple[str, ...]:
        """Return all registered provider names.

        Returns:
            Tuple of provider names.
        """
        return tuple(self._providers.keys())

    def has_provider(self, provider_name: str) -> bool:
        """Check if a provider is registered.

        Args:
            provider_name: Provider name.

        Returns:
            True if registered.
        """
        return provider_name in self._providers

    def has_type(self, data_type: DataType) -> bool:
        """Check if a data type has a registered provider.

        Args:
            data_type: Data type to check.

        Returns:
            True if a provider is registered for this type.
        """
        return data_type in self._type_map
