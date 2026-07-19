"""
Central registry for factor discovery and lookup.
"""

from __future__ import annotations

from typing import Type

from backend.factors.base import BaseFactor


class FactorRegistry:
    """Singleton registry that maps factor names to their classes.

    Factors are registered at import time and looked up by name
    at computation time. The registry prevents duplicate names and
    provides descriptive errors for debugging.

    Example::

        # Registration (typically done at module load time)
        FactorRegistry.register(SMA20)
        FactorRegistry.register(RSI14)

        # Lookup by name
        factor_cls = FactorRegistry.get("sma_20")
        factor = factor_cls()
        result = factor.compute(symbol="RELIANCE", prices=df)

        # Discovery
        all_factors = FactorRegistry.all()   # dict[str, Type[BaseFactor]]
        names = FactorRegistry.names()       # ["rsi_14", "sma_20"]

    Raises:
        ValueError: If a factor with the same name is registered twice.
        KeyError: If a factor name is not found in the registry.
    """

    _registry: dict[str, Type[BaseFactor]] = {}

    @classmethod
    def register(cls, factor_cls: Type[BaseFactor]) -> None:
        """Register a factor class in the global registry.

        The factor's name class attribute is used as the registry
        key. Duplicate names are rejected to prevent silent overrides.

        Args:
            factor_cls: A concrete subclass of BaseFactor.

        Raises:
            ValueError: If a factor with the same name is already
                        registered.
        """
        name = factor_cls.name
        if name in cls._registry:
            existing = cls._registry[name]
            raise ValueError(
                f"Factor '{name}' is already registered "
                f"({existing.__name__}). "
                f"Cannot register {factor_cls.__name__}."
            )
        cls._registry[name] = factor_cls

    @classmethod
    def get(cls, name: str) -> Type[BaseFactor]:
        """Retrieve a factor class by its unique name.

        Args:
            name: The factor's registered name (e.g. "sma_20").

        Returns:
            The BaseFactor subclass registered under that name.

        Raises:
            KeyError: If no factor with the given name exists.
                      The error message lists all available factors.
        """
        try:
            return cls._registry[name]
        except KeyError:
            available = ", ".join(sorted(cls._registry)) or "(none registered)"
            raise KeyError(
                f"Factor '{name}' not found. Available: {available}"
            ) from None

    @classmethod
    def all(cls) -> dict[str, Type[BaseFactor]]:
        """Return a shallow copy of all registered factors.

        Returns:
            A dictionary mapping factor names to their classes.
        """
        return dict(cls._registry)

    @classmethod
    def names(cls) -> list[str]:
        """Return a sorted list of all registered factor names.

        Returns:
            Sorted list of factor name strings.
        """
        return sorted(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        """Remove all registered factors.

        Intended for use in test teardown only. Not for production use.
        """
        cls._registry.clear()
