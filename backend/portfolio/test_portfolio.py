"""Portfolio management engine tests.

Covers all functionality including allocation, position management,
rebalancing, constraints, and metrics.
"""

from __future__ import annotations

import pytest

from backend.portfolio.allocation import (
    calculate_weights,
    equal_weight,
    fixed_weight,
    get_allocation_strategy,
    market_cap_weight,
    risk_weight,
    score_weight,
    validate_weights,
    volatility_weight,
)
from backend.portfolio.constraints import ConstraintValidator
from backend.portfolio.engine import PortfolioEngine
from backend.portfolio.exceptions import (
    AllocationError,
    ConstraintViolationError,
    EmptyPortfolioError,
    InsufficientFundsError,
    InvalidAllocationError,
    InvalidPortfolioConfigError,
    PortfolioError,
    PositionNotFoundError,
    RebalanceError,
)
from backend.portfolio.factory import PortfolioFactory
from backend.portfolio.models import (
    Allocation,
    AllocationStrategy,
    PortfolioConfig,
    PortfolioDefinition,
    PortfolioHolding,
    PortfolioMetadata,
    PortfolioMetrics,
    PortfolioPosition,
    PortfolioSnapshot,
    PortfolioStatistics,
    RebalanceAction,
    RebalanceActionType,
    RebalanceFrequency,
)
from backend.portfolio.positions import PositionManager
from backend.portfolio.rebalancer import Rebalancer


def _create_config(**kwargs: object) -> PortfolioConfig:
    """Create a test configuration."""
    defaults = {
        "initial_capital": 1_000_000.0,
        "max_positions": 50,
        "min_positions": 5,
        "max_position_size": 0.25,
        "min_position_size": 0.02,
        "cash_reserve": 0.05,
    }
    defaults.update(kwargs)
    return PortfolioConfig(**defaults)  # type: ignore[arg-type]


def _create_definition(**kwargs: object) -> PortfolioDefinition:
    """Create a test definition."""
    config = _create_config(**kwargs)
    return PortfolioDefinition(
        metadata=PortfolioMetadata(name="TestPortfolio"),
        config=config,
    )


def _create_positions(
    symbols: tuple[str, ...] = ("RELIANCE", "TCS", "INFY"),
    prices: dict[str, float] | None = None,
) -> list[PortfolioPosition]:
    """Create test positions."""
    if prices is None:
        prices = {"RELIANCE": 2500.0, "TCS": 3500.0, "INFY": 1400.0}

    positions = []
    for i, symbol in enumerate(symbols):
        price = prices.get(symbol, 2000.0)
        quantity = 100 + (i * 10)
        positions.append(
            PortfolioPosition(
                symbol=symbol,
                quantity=quantity,
                average_cost=price * 0.95,
                current_price=price,
                market_value=price * quantity,
                unrealized_pnl=price * quantity * 0.05,
                unrealized_pct=0.05,
                sector="Technology" if i % 2 == 0 else "Financials",
            )
        )
    return positions


class TestAllocationStrategies:
    """Test allocation strategies."""

    def test_equal_weight(self) -> None:
        symbols = ("A", "B", "C")
        config = _create_config()
        weights = equal_weight(symbols, {}, config)
        assert len(weights) == 3
        assert abs(sum(weights.values()) - 1.0) < 0.001
        assert all(abs(w - 1 / 3) < 0.001 for w in weights.values())

    def test_equal_weight_empty(self) -> None:
        config = _create_config()
        weights = equal_weight((), {}, config)
        assert weights == {}

    def test_fixed_weight(self) -> None:
        symbols = ("A", "B", "C")
        data = {"weights": {"A": 0.5, "B": 0.3, "C": 0.2}}
        config = _create_config()
        weights = fixed_weight(symbols, data, config)
        assert abs(weights["A"] - 0.5) < 0.001
        assert abs(weights["B"] - 0.3) < 0.001
        assert abs(weights["C"] - 0.2) < 0.001

    def test_fixed_weight_no_data(self) -> None:
        symbols = ("A", "B")
        config = _create_config()
        with pytest.raises(InvalidAllocationError):
            fixed_weight(symbols, {}, config)

    def test_risk_weight(self) -> None:
        symbols = ("A", "B")
        data = {"risk": {"A": 0.2, "B": 0.1}}
        config = _create_config()
        weights = risk_weight(symbols, data, config)
        assert weights["B"] > weights["A"]

    def test_risk_weight_no_data(self) -> None:
        symbols = ("A", "B")
        config = _create_config()
        with pytest.raises(InvalidAllocationError):
            risk_weight(symbols, {}, config)

    def test_volatility_weight(self) -> None:
        symbols = ("A", "B")
        data = {"volatility": {"A": 0.3, "B": 0.1}}
        config = _create_config()
        weights = volatility_weight(symbols, data, config)
        assert weights["B"] > weights["A"]

    def test_score_weight(self) -> None:
        symbols = ("A", "B", "C")
        data = {"scores": {"A": 80, "B": 90, "C": 70}}
        config = _create_config()
        weights = score_weight(symbols, data, config)
        assert weights["B"] > weights["A"] > weights["C"]

    def test_market_cap_weight(self) -> None:
        symbols = ("A", "B")
        data = {"market_cap": {"A": 1000, "B": 500}}
        config = _create_config()
        weights = market_cap_weight(symbols, data, config)
        assert weights["A"] > weights["B"]

    def test_get_allocation_strategy(self) -> None:
        fn = get_allocation_strategy(AllocationStrategy.EQUAL_WEIGHT)
        assert fn == equal_weight

    def test_get_allocation_strategy_invalid(self) -> None:
        with pytest.raises(InvalidAllocationError):
            get_allocation_strategy("INVALID")

    def test_calculate_weights(self) -> None:
        symbols = ("A", "B")
        config = _create_config()
        weights = calculate_weights(
            AllocationStrategy.EQUAL_WEIGHT, symbols, {}, config
        )
        assert len(weights) == 2

    def test_validate_weights(self) -> None:
        assert validate_weights({"A": 0.5, "B": 0.5}) is True

    def test_validate_weights_empty(self) -> None:
        with pytest.raises(InvalidAllocationError):
            validate_weights({})

    def test_validate_weights_wrong_sum(self) -> None:
        with pytest.raises(InvalidAllocationError):
            validate_weights({"A": 0.3, "B": 0.3})

    def test_validate_weights_negative(self) -> None:
        with pytest.raises(InvalidAllocationError):
            validate_weights({"A": 1.5, "B": -0.5})


class TestPositionManager:
    """Test position management."""

    def test_initialization(self) -> None:
        config = _create_config()
        manager = PositionManager(config)
        assert manager.get_total_value() == 0.0

    def test_open_position(self) -> None:
        config = _create_config()
        manager = PositionManager(config)
        position = manager.open_position("RELIANCE", 100, 2000.0)
        assert position.symbol == "RELIANCE"
        assert position.quantity == 100
        assert position.average_cost == 2000.0

    def test_add_to_position(self) -> None:
        config = _create_config()
        manager = PositionManager(config)
        manager.open_position("RELIANCE", 100, 2000.0)
        position = manager.add_to_position("RELIANCE", 50, 2100.0)
        assert position.quantity == 150
        assert position.average_cost == pytest.approx(2033.33, abs=0.01)

    def test_reduce_position(self) -> None:
        config = _create_config()
        manager = PositionManager(config)
        manager.open_position("RELIANCE", 100, 2000.0)
        position = manager.reduce_position("RELIANCE", 30, 2100.0)
        assert position.quantity == 70
        assert position.realized_pnl > 0

    def test_close_position(self) -> None:
        config = _create_config()
        manager = PositionManager(config)
        manager.open_position("RELIANCE", 100, 2000.0)
        position = manager.close_position("RELIANCE", 2100.0)
        assert position.quantity == 0
        assert position.realized_pnl > 0

    def test_position_not_found(self) -> None:
        config = _create_config()
        manager = PositionManager(config)
        with pytest.raises(PositionNotFoundError):
            manager.get_position("INVALID")

    def test_reduce_not_found(self) -> None:
        config = _create_config()
        manager = PositionManager(config)
        with pytest.raises(PositionNotFoundError):
            manager.reduce_position("INVALID", 10, 2000.0)

    def test_update_market_price(self) -> None:
        config = _create_config()
        manager = PositionManager(config)
        manager.open_position("RELIANCE", 100, 2000.0)
        manager.update_market_price("RELIANCE", 2100.0)
        position = manager.get_position("RELIANCE")
        assert position.current_price == 2100.0

    def test_get_all_positions(self) -> None:
        config = _create_config()
        manager = PositionManager(config)
        manager.open_position("RELIANCE", 100, 2000.0)
        manager.open_position("TCS", 50, 3500.0)
        positions = manager.get_all_positions()
        assert len(positions) == 2

    def test_get_active_symbols(self) -> None:
        config = _create_config()
        manager = PositionManager(config)
        manager.open_position("RELIANCE", 100, 2000.0)
        manager.close_position("RELIANCE", 2100.0)
        symbols = manager.get_active_symbols()
        assert "RELIANCE" not in symbols

    def test_get_total_value(self) -> None:
        config = _create_config()
        manager = PositionManager(config)
        manager.open_position("RELIANCE", 100, 2000.0)
        manager.update_market_price("RELIANCE", 2100.0)
        assert manager.get_total_value() == 210000.0

    def test_sector_exposure(self) -> None:
        config = _create_config()
        manager = PositionManager(config)
        manager.open_position("RELIANCE", 100, 2000.0, "Energy")
        manager.open_position("TCS", 50, 3500.0, "Technology")
        manager.update_all_prices({"RELIANCE": 2000.0, "TCS": 3500.0})
        exposure = manager.get_sector_exposure()
        assert "Energy" in exposure
        assert "Technology" in exposure


class TestConstraintValidator:
    """Test constraint validation."""

    def test_initialization(self) -> None:
        config = _create_config()
        validator = ConstraintValidator(config)
        assert validator.config == config

    def test_check_position_count(self) -> None:
        config = _create_config(max_positions=2, min_positions=1)
        validator = ConstraintValidator(config)
        positions = _create_positions(("A", "B", "C"))
        with pytest.raises(ConstraintViolationError):
            validator.check_position_count(positions)

    def test_check_position_count_min(self) -> None:
        config = _create_config(min_positions=5)
        validator = ConstraintValidator(config)
        positions = _create_positions(("A",))
        with pytest.raises(ConstraintViolationError):
            validator.check_position_count(positions)

    def test_check_position_sizes(self) -> None:
        config = _create_config(max_position_size=0.10)
        validator = ConstraintValidator(config)
        positions = [
            PortfolioPosition(
                symbol="A",
                quantity=100,
                market_value=200000,
            )
        ]
        with pytest.raises(ConstraintViolationError):
            validator.check_position_sizes(positions, 1000000)

    def test_check_cash_reserve(self) -> None:
        config = _create_config(cash_reserve=0.10)
        validator = ConstraintValidator(config)
        with pytest.raises(ConstraintViolationError):
            validator.check_cash_reserve(50000, 1000000)

    def test_check_sector_exposure(self) -> None:
        config = _create_config(max_sector_exposure=0.20)
        validator = ConstraintValidator(config)
        positions = [
            PortfolioPosition(symbol="A", quantity=100, market_value=300000, sector="Tech"),
            PortfolioPosition(symbol="B", quantity=100, market_value=300000, sector="Tech"),
        ]
        with pytest.raises(ConstraintViolationError):
            validator.check_sector_exposure(positions, 1000000)

    def test_check_stock_exposure(self) -> None:
        config = _create_config(max_stock_exposure=0.15)
        validator = ConstraintValidator(config)
        positions = [
            PortfolioPosition(symbol="A", quantity=100, market_value=200000),
        ]
        with pytest.raises(ConstraintViolationError):
            validator.check_stock_exposure(positions, 1000000)

    def test_validate_all(self) -> None:
        config = _create_config(max_positions=2)
        validator = ConstraintValidator(config)
        positions = _create_positions(("A", "B", "C"))
        violations = validator.validate_all(positions, 100000, 1000000)
        assert len(violations) > 0


class TestRebalancer:
    """Test rebalancing."""

    def test_initialization(self) -> None:
        config = _create_config()
        rebalancer = Rebalancer(config)
        assert rebalancer.config == config
        assert rebalancer.last_rebalance is None

    def test_should_rebalance_first_time(self) -> None:
        config = _create_config()
        rebalancer = Rebalancer(config)
        positions = _create_positions()
        assert rebalancer.should_rebalance(positions, 1000000) is True

    def test_generate_actions(self) -> None:
        config = _create_config()
        rebalancer = Rebalancer(config)
        positions = _create_positions()
        target = {"RELIANCE": 0.4, "TCS": 0.3, "INFY": 0.3}
        prices = {"RELIANCE": 2500.0, "TCS": 3500.0, "INFY": 1400.0}
        actions = rebalancer.generate_actions(positions, target, 1000000, prices)
        assert len(actions) > 0

    def test_filter_actions(self) -> None:
        config = _create_config(cash_reserve=0.10)
        rebalancer = Rebalancer(config)
        actions = [
            RebalanceAction(
                symbol="A",
                action_type=RebalanceActionType.BUY,
                quantity=100,
                current_weight=0.0,
                target_weight=0.2,
                current_value=0,
                target_value=200000,
                drift=-0.2,
            )
        ]
        filtered = rebalancer.filter_actions(actions, 50000, 1000000)
        assert isinstance(filtered, list)


class TestPortfolioEngine:
    """Test portfolio engine."""

    def test_initialization(self) -> None:
        engine = PortfolioEngine()
        assert engine.cash == 0.0

    def test_create_portfolio(self) -> None:
        definition = _create_definition()
        engine = PortfolioEngine()
        snapshot = engine.create_portfolio(definition)
        assert isinstance(snapshot, PortfolioSnapshot)
        assert engine.cash == 1_000_000.0

    def test_allocate(self) -> None:
        definition = _create_definition()
        engine = PortfolioEngine()
        engine.create_portfolio(definition)
        symbols = ("RELIANCE", "TCS", "INFY")
        prices = {"RELIANCE": 2500.0, "TCS": 3500.0, "INFY": 1400.0}
        allocations = engine.allocate(symbols, {}, prices)
        assert len(allocations) > 0
        assert sum(a.weight for a in allocations) == pytest.approx(1.0, abs=0.01)

    def test_execute_allocations(self) -> None:
        definition = _create_definition()
        engine = PortfolioEngine()
        engine.create_portfolio(definition)
        allocations = [
            Allocation(symbol="RELIANCE", weight=0.5, amount=500000),
        ]
        prices = {"RELIANCE": 2500.0}
        snapshot = engine.execute_allocations(allocations, prices)
        assert snapshot.holdings_value > 0

    def test_rebalance(self) -> None:
        definition = _create_definition()
        engine = PortfolioEngine()
        engine.create_portfolio(definition)

        allocations = [
            Allocation(symbol="RELIANCE", weight=0.5, amount=500000),
            Allocation(symbol="TCS", weight=0.5, amount=500000),
        ]
        prices = {"RELIANCE": 2500.0, "TCS": 3500.0}
        engine.execute_allocations(allocations, prices)

        target = {"RELIANCE": 0.4, "TCS": 0.6}
        actions = engine.rebalance(target, prices)
        assert isinstance(actions, list)

    def test_update_market_values(self) -> None:
        definition = _create_definition()
        engine = PortfolioEngine()
        engine.create_portfolio(definition)

        allocations = [
            Allocation(symbol="RELIANCE", weight=1.0, amount=950000),
        ]
        prices = {"RELIANCE": 2500.0}
        engine.execute_allocations(allocations, prices)

        snapshot = engine.update_market_values({"RELIANCE": 2600.0})
        assert snapshot.holdings_value > 0

    def test_evaluate_constraints(self) -> None:
        definition = _create_definition(min_positions=10)
        engine = PortfolioEngine()
        engine.create_portfolio(definition)
        violations = engine.evaluate_constraints()
        assert isinstance(violations, list)

    def test_generate_snapshot(self) -> None:
        definition = _create_definition()
        engine = PortfolioEngine()
        engine.create_portfolio(definition)
        snapshot = engine.generate_snapshot()
        assert isinstance(snapshot, PortfolioSnapshot)
        assert snapshot.total_equity == 1_000_000.0

    def test_get_metrics(self) -> None:
        definition = _create_definition()
        engine = PortfolioEngine()
        engine.create_portfolio(definition)
        metrics = engine.get_metrics()
        assert isinstance(metrics, PortfolioMetrics)


class TestPortfolioFactory:
    """Test factory creation."""

    def test_create_default(self) -> None:
        engine = PortfolioFactory.create()
        assert isinstance(engine, PortfolioEngine)

    def test_create_with_config(self) -> None:
        config = _create_config()
        engine = PortfolioFactory.create(config=config)
        assert isinstance(engine, PortfolioEngine)

    def test_create_with_config_method(self) -> None:
        config = _create_config()
        engine = PortfolioFactory.create_with_config(config)
        assert isinstance(engine, PortfolioEngine)

    def test_create_from_definition(self) -> None:
        definition = _create_definition()
        engine = PortfolioFactory.create_from_definition(definition)
        assert isinstance(engine, PortfolioEngine)
        assert engine.cash == 1_000_000.0


class TestModels:
    """Test data models."""

    def test_portfolio_metadata(self) -> None:
        metadata = PortfolioMetadata(name="Test")
        assert metadata.name == "Test"
        assert metadata.version == "1.0"

    def test_portfolio_config(self) -> None:
        config = PortfolioConfig()
        assert config.initial_capital == 1_000_000.0
        assert config.max_positions == 50

    def test_portfolio_definition(self) -> None:
        definition = PortfolioDefinition(
            metadata=PortfolioMetadata(name="Test"),
            config=PortfolioConfig(),
        )
        assert definition.metadata.name == "Test"

    def test_portfolio_holding(self) -> None:
        holding = PortfolioHolding(
            symbol="RELIANCE",
            quantity=100,
            average_cost=2000.0,
            current_price=2100.0,
        )
        assert holding.symbol == "RELIANCE"
        assert holding.market_value == 0.0

    def test_portfolio_position(self) -> None:
        position = PortfolioPosition(
            symbol="RELIANCE",
            quantity=100,
            average_cost=2000.0,
            current_price=2100.0,
            market_value=210000,
            unrealized_pnl=10000,
        )
        assert position.symbol == "RELIANCE"
        assert position.unrealized_pnl == 10000

    def test_allocation(self) -> None:
        alloc = Allocation(symbol="RELIANCE", weight=0.5, amount=500000)
        assert alloc.symbol == "RELIANCE"
        assert alloc.weight == 0.5

    def test_rebalance_action(self) -> None:
        action = RebalanceAction(
            symbol="RELIANCE",
            action_type=RebalanceActionType.BUY,
            quantity=100,
        )
        assert action.symbol == "RELIANCE"
        assert action.action_type == RebalanceActionType.BUY

    def test_portfolio_snapshot(self) -> None:
        snapshot = PortfolioSnapshot(
            cash=500000,
            holdings_value=500000,
            total_equity=1000000,
        )
        assert snapshot.total_equity == 1000000

    def test_portfolio_metrics(self) -> None:
        metrics = PortfolioMetrics(
            portfolio_return=0.15,
            sharpe_ratio=1.2,
        )
        assert metrics.portfolio_return == 0.15

    def test_portfolio_statistics(self) -> None:
        stats = PortfolioStatistics(total_positions=10)
        assert stats.total_positions == 10

    def test_allocation_strategy(self) -> None:
        assert AllocationStrategy.EQUAL_WEIGHT == "EQUAL_WEIGHT"

    def test_rebalance_frequency(self) -> None:
        assert RebalanceFrequency.MONTHLY == "MONTHLY"

    def test_rebalance_action_type(self) -> None:
        assert RebalanceActionType.BUY == "BUY"


class TestExceptions:
    """Test exception hierarchy."""

    def test_portfolio_error(self) -> None:
        with pytest.raises(PortfolioError):
            raise PortfolioError("test")

    def test_invalid_portfolio_config_error(self) -> None:
        with pytest.raises(InvalidPortfolioConfigError):
            raise InvalidPortfolioConfigError("test")

    def test_constraint_violation_error(self) -> None:
        with pytest.raises(ConstraintViolationError):
            raise ConstraintViolationError("test", "test")

    def test_insufficient_funds_error(self) -> None:
        with pytest.raises(InsufficientFundsError):
            raise InsufficientFundsError(1000.0, 500.0)

    def test_allocation_error(self) -> None:
        with pytest.raises(AllocationError):
            raise AllocationError("test")

    def test_rebalance_error(self) -> None:
        with pytest.raises(RebalanceError):
            raise RebalanceError("test")

    def test_position_not_found_error(self) -> None:
        with pytest.raises(PositionNotFoundError):
            raise PositionNotFoundError("RELIANCE")

    def test_empty_portfolio_error(self) -> None:
        with pytest.raises(EmptyPortfolioError):
            raise EmptyPortfolioError()

    def test_invalid_allocation_error(self) -> None:
        with pytest.raises(InvalidAllocationError):
            raise InvalidAllocationError("test")


class TestIntegration:
    """Integration tests for complete portfolio flow."""

    def test_complete_portfolio_flow(self) -> None:
        definition = _create_definition()
        engine = PortfolioFactory.create_from_definition(definition)

        symbols = ("RELIANCE", "TCS", "INFY")
        prices = {"RELIANCE": 2500.0, "TCS": 3500.0, "INFY": 1400.0}

        allocations = engine.allocate(symbols, {}, prices)
        assert len(allocations) > 0

        snapshot = engine.execute_allocations(allocations, prices)
        assert snapshot.holdings_value > 0

        violations = engine.evaluate_constraints()
        assert isinstance(violations, list)

        metrics = engine.get_metrics()
        assert isinstance(metrics, PortfolioMetrics)

    def test_rebalancing_flow(self) -> None:
        definition = _create_definition()
        engine = PortfolioFactory.create_from_definition(definition)

        allocations = [
            Allocation(symbol="RELIANCE", weight=0.5, amount=475000),
            Allocation(symbol="TCS", weight=0.5, amount=475000),
        ]
        prices = {"RELIANCE": 2500.0, "TCS": 3500.0}
        engine.execute_allocations(allocations, prices)

        target = {"RELIANCE": 0.4, "TCS": 0.6}
        actions = engine.rebalance(target, prices)
        assert isinstance(actions, list)

        snapshot = engine.generate_snapshot()
        assert snapshot.total_equity > 0
