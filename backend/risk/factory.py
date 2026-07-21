"""Risk factory.

Constructs fully configured risk engines using dependency injection.
"""

from __future__ import annotations

from backend.risk.engine import RiskEngine
from backend.risk.models import RiskConfig
from backend.risk.scenarios import ScenarioRegistry, build_default_registry


class RiskFactory:
    """Factory for constructing fully configured RiskEngine instances.

    Uses dependency injection to construct all required components.
    No global state is maintained.
    """

    @staticmethod
    def create(
        config: RiskConfig | None = None,
        scenario_registry: ScenarioRegistry | None = None,
    ) -> RiskEngine:
        """Create a fully configured RiskEngine.

        Args:
            config:           Risk configuration (defaults created).
            scenario_registry: Registry of scenarios (defaults created).

        Returns:
            Configured RiskEngine instance.
        """
        scenario_registry = scenario_registry or build_default_registry()

        return RiskEngine(scenario_registry=scenario_registry)

    @staticmethod
    def create_with_custom_scenarios() -> RiskEngine:
        """Create a RiskEngine with an empty scenario registry.

        Useful for applications that only want custom scenarios.

        Returns:
            RiskEngine with no pre-registered scenarios.
        """
        return RiskEngine(scenario_registry=ScenarioRegistry())

    @staticmethod
    def create_from_registry(scenario_registry: ScenarioRegistry) -> RiskEngine:
        """Create a RiskEngine from an existing registry.

        Args:
            scenario_registry: Pre-configured scenario registry.

        Returns:
            RiskEngine using the provided registry.
        """
        return RiskEngine(scenario_registry=scenario_registry)
