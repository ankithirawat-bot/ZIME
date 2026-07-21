"""Portfolio factory.

Constructs fully configured portfolio engines using dependency injection.
"""

from __future__ import annotations

from backend.portfolio.constraints import ConstraintValidator
from backend.portfolio.engine import PortfolioEngine
from backend.portfolio.models import PortfolioConfig, PortfolioDefinition
from backend.portfolio.positions import PositionManager
from backend.portfolio.rebalancer import Rebalancer


class PortfolioFactory:
    """Factory for constructing fully configured PortfolioEngine instances.

    Uses dependency injection to construct all required components.
    No global state is maintained.
    """

    @staticmethod
    def create(
        config: PortfolioConfig | None = None,
        position_manager: PositionManager | None = None,
        rebalancer: Rebalancer | None = None,
        constraint_validator: ConstraintValidator | None = None,
    ) -> PortfolioEngine:
        """Create a fully configured PortfolioEngine.

        Args:
        Args:
            config:              Portfolio configuration (defaults created).
            position_manager:    Position manager (defaults created).
            rebalancer:          Rebalancer (defaults created).
            constraint_validator: Constraint validator (defaults created).

        Returns:
            Configured PortfolioEngine instance.
        """
        config = config or PortfolioConfig()
        position_manager = position_manager or PositionManager(config)
        rebalancer = rebalancer or Rebalancer(config)
        constraint_validator = constraint_validator or ConstraintValidator(config)

        return PortfolioEngine(
            position_manager=position_manager,
            rebalancer=rebalancer,
            constraint_validator=constraint_validator,
        )

    @staticmethod
    def create_with_config(config: PortfolioConfig) -> PortfolioEngine:
        """Create a PortfolioEngine with specific configuration.

        Args:
            config: Portfolio configuration.

        Returns:
            PortfolioEngine with the provided configuration.
        """
        return PortfolioFactory.create(config=config)

    @staticmethod
    def create_from_definition(
        definition: PortfolioDefinition,
    ) -> PortfolioEngine:
        """Create a PortfolioEngine from a definition.

        Args:
            definition: Portfolio definition.

        Returns:
            PortfolioEngine created from definition.
        """
        engine = PortfolioFactory.create(config=definition.config)
        engine.create_portfolio(definition)
        return engine
