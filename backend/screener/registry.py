"""Screener filter registry.

Maintains a registry of available filters for extensibility.
"""

from __future__ import annotations

from backend.screener.exceptions import FilterNotFoundError
from backend.screener.filters import FilterFunc, get_builtin_filters
from backend.screener.models import FilterCategory


class FilterRegistry:
    """Registry of screen filters.

    Supports custom filters without modifying engine code.
    """

    def __init__(self, *, load_defaults: bool = True) -> None:
        """Initialize the registry.

        Args:
            load_defaults: Whether to load built-in filters.
        """
        self._filters: dict[str, tuple[FilterCategory, FilterFunc]] = {}
        if load_defaults:
            self._filters.update(get_builtin_filters())

    def register(
        self,
        name: str,
        func: FilterFunc,
        category: FilterCategory = FilterCategory.CUSTOM,
    ) -> None:
        """Register a filter.

        Args:
            name:     Filter name.
            func:     Filter function.
            category: Filter category.
        """
        self._filters[name] = (category, func)

    def get(self, name: str) -> FilterFunc:
        """Get a filter function by name.

        Args:
            name: Filter name.

        Returns:
            The filter function.

        Raises:
            FilterNotFoundError: If the filter is not registered.
        """
        if name not in self._filters:
            raise FilterNotFoundError(name)
        _, func = self._filters[name]
        return func

    def get_category(self, name: str) -> FilterCategory:
        """Get the category of a filter.

        Args:
            name: Filter name.

        Returns:
            The filter category.

        Raises:
            FilterNotFoundError: If the filter is not registered.
        """
        if name not in self._filters:
            raise FilterNotFoundError(name)
        category, _ = self._filters[name]
        return category

    def is_registered(self, name: str) -> bool:
        """Check if a filter is registered."""
        return name in self._filters

    def registered_names(self) -> tuple[str, ...]:
        """Return all registered filter names."""
        return tuple(sorted(self._filters.keys()))

    def filters_by_category(self, category: FilterCategory) -> tuple[str, ...]:
        """Return filter names for a given category."""
        return tuple(
            sorted(name for name, (cat, _) in self._filters.items() if cat == category)
        )

    def all_filters(self) -> dict[str, tuple[FilterCategory, FilterFunc]]:
        """Return a copy of all registered filters."""
        return dict(self._filters)


def build_default_filter_registry() -> FilterRegistry:
    """Build a filter registry with all built-in filters.

    Returns:
        A FilterRegistry with all built-in filters loaded.
    """
    return FilterRegistry(load_defaults=True)
