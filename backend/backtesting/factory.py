"""Backtesting factory.

Constructs fully configured backtesting engines using dependency injection.
"""

from __future__ import annotations

from backend.backtesting.broker import Broker
from backend.backtesting.engine import BacktestEngine
from backend.backtesting.models import BacktestConfig
from backend.backtesting.portfolio import Portfolio


class BacktestFactory:
    """Factory for constructing fully configured BacktestEngine instances.

    Uses dependency injection to construct all required components.
    No global state is maintained.
    """

    @staticmethod
    def create(
        config: BacktestConfig | None = None,
        broker: Broker | None = None,
        portfolio: Portfolio | None = None,
    ) -> BacktestEngine:
        """Create a fully configured BacktestEngine.

        Args:
            config:    Backtest configuration (defaults created).
            broker:    Broker for order execution (defaults created).
            portfolio: Portfolio to manage (defaults created).

        Returns:
            Configured BacktestEngine instance.
        """
        config = config or BacktestConfig()
        broker = broker or Broker(config)
        portfolio = portfolio or Portfolio(config, broker)

        return BacktestEngine(broker=broker, portfolio=portfolio)

    @staticmethod
    def create_with_custom_broker(
        config: BacktestConfig,
        broker: Broker,
    ) -> BacktestEngine:
        """Create a BacktestEngine with a custom broker.

        Args:
            config: Backtest configuration.
            broker: Custom broker.

        Returns:
            BacktestEngine using the provided broker.
        """
        portfolio = Portfolio(config, broker)
        return BacktestEngine(broker=broker, portfolio=portfolio)

    @staticmethod
    def create_from_config(config: BacktestConfig) -> BacktestEngine:
        """Create a BacktestEngine from configuration only.

        Args:
            config: Backtest configuration.

        Returns:
            BacktestEngine with default components.
        """
        broker = Broker(config)
        portfolio = Portfolio(config, broker)
        return BacktestEngine(broker=broker, portfolio=portfolio)
