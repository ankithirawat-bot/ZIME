"""Factory for creating optimization engine instances.
Provides dependency injection and lifecycle management for optimization engines.
"""

from __future__ import annotations

from backend.optimization.engine import OptimizationEngine
from backend.optimization.exceptions import OptimizationError
from backend.optimization.models import OptimizationConfig, ObjectiveType



class OptimizationFactory:
    """Factory for creating and configuring optimization engines to avoid circular imports."""

    @classmethod
    def create(cls) -> OptimizationEngine:
        """Create a default optimization engine."""
        return cls.create_with_config(OptimizationConfig())

    @classmethod
    def create_from_config(cls, config: OptimizationConfig) -> OptimizationEngine:
        """Create an engine from a provided config (alias for test_optimization compat)."""
        return cls.create_with_config(config)

    @classmethod
    def create_with_config(cls, config: OptimizationConfig) -> OptimizationEngine:
        """Create an optimization engine with the given configuration.

        Args:
            config: Optimization configuration

        Returns:
            Configured optimization engine

        Raises:
            OptimizationError: If engine creation fails
        """
        try:
            return OptimizationEngine(config)
        except Exception as e:
            msg = f"Failed to create optimization engine: {e}"
            raise OptimizationError(msg) from e

    @classmethod
    def create_with_objective(cls, objective: ObjectiveType, **overrides) -> OptimizationEngine:
        """Create an engine with a specific objective (alias per Sprint 42B spec)."""
        cfg = OptimizationConfig(objective=objective, **overrides)
        return cls.create_with_config(cfg)
