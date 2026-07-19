"""
Registry for all factors.
"""

from __future__ import annotations

from typing import Dict, Type

from backend.factors.base import BaseFactor


class FactorRegistry:

    _registry: Dict[str, Type[BaseFactor]] = {}

    @classmethod
    def register(cls, factor: Type[BaseFactor]) -> None:
        cls._registry[factor.name] = factor

    @classmethod
    def get(cls, name: str) -> Type[BaseFactor]:
        return cls._registry[name]

    @classmethod
    def all(cls):
        return cls._registry