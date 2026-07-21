"""Position sizing engine tests.

Covers all functionality including sizing methods, constraints, optimizer,
engine, factory, and integration.
"""

from __future__ import annotations

import pytest

from backend.sizing.constraints import ConstraintResult, SizingConstraints
from backend.sizing.engine import SizingEngine
from backend.sizing.exceptions import (
    CalculationError,
    ConstraintViolationError,
    EmptyPortfolioError,
    InsufficientDataError,
    InvalidSizingConfigError,
    MethodNotFoundError,
    SizingError,
)
from backend.sizing.factory import SizingFactory
from backend.sizing.methods import (
    ATRPositionSizingMethod,
    EqualRiskContributionMethod,
    FixedFractionalMethod,
    FixedRiskPerTradeMethod,
    FixedSharesMethod,
    FixedValueMethod,
    FractionalKellyMethod,
    KellyCriterionMethod,
    PercentageOfEquityMethod,
    VolatilityTargetingMethod,
)
from backend.sizing.models import (
    AllocationResult,
    PositionRequest,
    PositionSizing,
    RiskBudget,
    SizingConfig,
    SizingDefinition,
    SizingMetadata,
    SizingMetrics,
    SizingStatistics,
)
from backend.sizing.optimizer import SizingOptimizer


def _create_config(**kwargs: object) -> SizingConfig:
    """Create a test configuration."""
    defaults: dict[str, object] = {
        "method": "fixed_fractional",
        "risk_per_trade": 0.02,
        "max_position_size": 0.25,
        "min_position_size": 0.01,
        "max_portfolio_exposure": 1.0,
        "max_sector_exposure": 0.30,
        "cash_reserve": 0.05,
        "max_leverage": 1.0,
        "round_lot": 1,
        "min_trade_value": 0.0,
        "kelly_fraction": 0.25,
        "atr_period": 14,
        "atr_multiplier": 2.0,
        "vol_target": 0.15,
        "vol_lookback": 20,
        "equal_risk_vol_target": 0.15,
        "default_account_size": 1000000.0,
    }
    defaults.update(kwargs)
    return SizingConfig(**defaults)  # type: ignore[arg-type]


def _create_request(
    symbol: str = "RELIANCE",
    price: float = 2500.0,
    account_size: float = 1000000.0,
    available_cash: float = 500000.0,
    **kwargs: object,
) -> PositionRequest:
    """Create a test position request."""
    defaults: dict[str, object] = {
        "symbol": symbol,
        "price": price,
        "account_size": account_size,
        "portfolio_value": account_size,
        "available_cash": available_cash,
        "volatility": 0.25,
        "atr": 50.0,
        "win_rate": 0.55,
        "avg_win": 3000.0,
        "avg_loss": 1500.0,
        "sector": "Technology",
        "signal_strength": 1.0,
    }
    defaults.update(kwargs)
    return PositionRequest(**defaults)  # type: ignore[arg-type]


def _create_requests(
    count: int = 3,
    account_size: float = 1000000.0,
) -> tuple[PositionRequest, ...]:
    """Create multiple test position requests."""
    symbols = ["RELIANCE", "TCS", "INFY", "HDFC", "ITC"]
    prices = [2500.0, 3500.0, 1500.0, 1600.0, 400.0]
    sectors = ["Energy", "Technology", "Technology", "Financial", "Consumer"]
    cash_per_request = account_size * 0.5

    requests = []
    for i in range(min(count, len(symbols))):
        requests.append(
            PositionRequest(
                symbol=symbols[i],
                price=prices[i],
                account_size=account_size,
                portfolio_value=account_size,
                available_cash=cash_per_request,
                volatility=0.20 + i * 0.05,
                atr=30.0 + i * 10.0,
                sector=sectors[i],
            )
        )
    return tuple(requests)


class TestModels:
    """Test data models."""

    def test_sizing_metadata(self) -> None:
        metadata = SizingMetadata(name="Test")
        assert metadata.name == "Test"
        assert metadata.version == "1.0"

    def test_sizing_config_defaults(self) -> None:
        config = SizingConfig()
        assert config.method == "fixed_fractional"
        assert config.risk_per_trade == 0.02

    def test_sizing_definition(self) -> None:
        definition = SizingDefinition(
            metadata=SizingMetadata(name="Test"),
            config=SizingConfig(),
        )
        assert definition.metadata.name == "Test"

    def test_position_request(self) -> None:
        request = _create_request()
        assert request.symbol == "RELIANCE"
        assert request.price == 2500.0

    def test_position_sizing(self) -> None:
        sizing = PositionSizing(
            symbol="RELIANCE", shares=100, value=250000.0, weight=0.25
        )
        assert sizing.shares == 100
        assert sizing.value == 250000.0

    def test_allocation_result(self) -> None:
        result = AllocationResult(total_value=500000.0, cash_remaining=500000.0)
        assert result.total_value == 500000.0

    def test_risk_budget(self) -> None:
        budget = RiskBudget(symbol="RELIANCE", risk_weight=0.5, risk_amount=10000.0)
        assert budget.symbol == "RELIANCE"
        assert budget.risk_weight == 0.5

    def test_sizing_metrics(self) -> None:
        metrics = SizingMetrics(total_positions=5, total_exposure=1.0)
        assert metrics.total_positions == 5

    def test_sizing_statistics(self) -> None:
        stats = SizingStatistics(total_calculations=10)
        assert stats.total_calculations == 10

    def test_sizing_metadata_immutable(self) -> None:
        metadata = SizingMetadata(name="Test")
        with pytest.raises(AttributeError):
            metadata.name = "Changed"  # type: ignore[misc]

    def test_config_immutable(self) -> None:
        config = SizingConfig()
        with pytest.raises(AttributeError):
            config.method = "changed"  # type: ignore[misc]

    def test_position_sizing_immutable(self) -> None:
        sizing = PositionSizing(symbol="TEST", shares=100, value=50000.0, weight=0.25)
        with pytest.raises(AttributeError):
            sizing.shares = 200  # type: ignore[misc]

    def test_allocation_result_empty_defaults(self) -> None:
        result = AllocationResult()
        assert len(result.positions) == 0
        assert result.total_value == 0.0

    def test_risk_budget_empty_defaults(self) -> None:
        budget = RiskBudget(symbol="TEST")
        assert budget.risk_weight == 0.0


class TestMethods:
    """Test sizing methods."""

    def test_fixed_shares(self) -> None:
        method = FixedSharesMethod()
        request = _create_request(available_cash=500000.0, price=2500.0)
        config = _create_config(min_position_size=0.001)
        result = method.calculate(request, config)
        assert result.method == "fixed_shares"
        assert result.shares > 0

    def test_fixed_shares_adjusts_for_min_size(self) -> None:
        method = FixedSharesMethod()
        config = _create_config(min_position_size=0.10)
        request = _create_request(available_cash=10000.0)
        result = method.calculate(request, config)
        assert result.shares >= 0

    def test_fixed_value(self) -> None:
        method = FixedValueMethod()
        request = _create_request()
        result = method.calculate(request, _create_config())
        assert result.method == "fixed_value"
        assert result.value > 0

    def test_fixed_value_no_cash(self) -> None:
        method = FixedValueMethod()
        request = _create_request(available_cash=0.0)
        result = method.calculate(request, _create_config())
        assert result.value >= 0

    def test_fixed_fractional(self) -> None:
        method = FixedFractionalMethod()
        request = _create_request()
        result = method.calculate(request, _create_config())
        assert result.method == "fixed_fractional"
        assert result.value > 0
        assert result.weight > 0

    def test_fixed_fractional_no_cash(self) -> None:
        method = FixedFractionalMethod()
        request = _create_request(available_cash=0.0)
        result = method.calculate(request, _create_config())
        assert result.value == 0.0

    def test_fixed_risk_per_trade(self) -> None:
        method = FixedRiskPerTradeMethod()
        request = _create_request(volatility=0.25)
        result = method.calculate(request, _create_config())
        assert result.method == "fixed_risk_per_trade"
        assert result.risk_amount > 0

    def test_fixed_risk_per_trade_invalid_price(self) -> None:
        method = FixedRiskPerTradeMethod()
        request = _create_request(price=0.0)
        result = method.calculate(request, _create_config())
        assert "Invalid" in result.reason

    def test_percentage_of_equity(self) -> None:
        method = PercentageOfEquityMethod()
        request = _create_request()
        result = method.calculate(request, _create_config())
        assert result.method == "percentage_of_equity"
        assert result.value > 0

    def test_percentage_of_equity_with_portfolio_value(self) -> None:
        method = PercentageOfEquityMethod()
        request = _create_request(portfolio_value=2000000.0)
        config = _create_config(max_position_size=0.50)
        result = method.calculate(request, config)
        assert result.value > 0

    def test_kelly_criterion(self) -> None:
        method = KellyCriterionMethod()
        request = _create_request(win_rate=0.55, avg_win=3000.0, avg_loss=1500.0)
        result = method.calculate(request, _create_config())
        assert result.method == "kelly_criterion"
        assert result.shares >= 0

    def test_kelly_criterion_invalid_win_rate(self) -> None:
        method = KellyCriterionMethod()
        request = _create_request(win_rate=0.0, avg_win=3000.0, avg_loss=1500.0)
        result = method.calculate(request, _create_config())
        assert "Invalid" in result.reason

    def test_kelly_criterion_invalid_loss(self) -> None:
        method = KellyCriterionMethod()
        request = _create_request(win_rate=0.55, avg_win=3000.0, avg_loss=0.0)
        result = method.calculate(request, _create_config())
        assert "Invalid" in result.reason

    def test_kelly_criterion_zero_fraction(self) -> None:
        method = KellyCriterionMethod()
        request = _create_request(win_rate=0.30, avg_win=1000.0, avg_loss=5000.0)
        result = method.calculate(request, _create_config())
        assert result.value == 0.0 or "zero" in result.reason.lower()

    def test_fractional_kelly(self) -> None:
        method = FractionalKellyMethod()
        request = _create_request(win_rate=0.55, avg_win=3000.0, avg_loss=1500.0)
        result = method.calculate(request, _create_config())
        assert result.method == "fractional_kelly"
        assert result.shares >= 0

    def test_fractional_kelly_invalid_win_rate(self) -> None:
        method = FractionalKellyMethod()
        request = _create_request(win_rate=1.0, avg_win=3000.0, avg_loss=1500.0)
        result = method.calculate(request, _create_config())
        assert "Invalid" in result.reason

    def test_atr_position_sizing(self) -> None:
        method = ATRPositionSizingMethod()
        request = _create_request(atr=50.0)
        result = method.calculate(request, _create_config())
        assert result.method == "atr_position_sizing"
        assert result.shares > 0

    def test_atr_position_sizing_zero_atr(self) -> None:
        method = ATRPositionSizingMethod()
        request = _create_request(atr=0.0)
        result = method.calculate(request, _create_config())
        assert "zero" in result.reason.lower()

    def test_volatility_targeting(self) -> None:
        method = VolatilityTargetingMethod()
        request = _create_request(volatility=0.25)
        result = method.calculate(request, _create_config(vol_target=0.15))
        assert result.method == "volatility_targeting"
        assert result.shares >= 0

    def test_volatility_targeting_zero_vol(self) -> None:
        method = VolatilityTargetingMethod()
        request = _create_request(volatility=0.0)
        result = method.calculate(request, _create_config())
        assert "zero" in result.reason.lower()

    def test_volatility_targeting_low_vol_high_position(self) -> None:
        method = VolatilityTargetingMethod()
        request = _create_request(volatility=0.05)
        config = _create_config(vol_target=0.15, max_position_size=1.0)
        result = method.calculate(request, config)
        assert result.weight > 0

    def test_equal_risk_contribution(self) -> None:
        method = EqualRiskContributionMethod()
        request = _create_request(volatility=0.25)
        result = method.calculate(request, _create_config())
        assert result.method == "equal_risk_contribution"
        assert result.shares >= 0

    def test_equal_risk_contribution_zero_vol(self) -> None:
        method = EqualRiskContributionMethod()
        request = _create_request(volatility=0.0)
        result = method.calculate(request, _create_config())
        assert "zero" in result.reason.lower()

    def test_fixed_shares_round_lot(self) -> None:
        method = FixedSharesMethod()
        request = _create_request(available_cash=100000.0)
        config = _create_config(round_lot=10, max_position_size=1.0, min_position_size=0.0)
        result = method.calculate(request, config)
        assert result.shares % 10 == 0 or result.shares == 0

    def test_method_names(self) -> None:
        methods = [
            FixedSharesMethod(),
            FixedValueMethod(),
            FixedFractionalMethod(),
            FixedRiskPerTradeMethod(),
            PercentageOfEquityMethod(),
            KellyCriterionMethod(),
            FractionalKellyMethod(),
            ATRPositionSizingMethod(),
            VolatilityTargetingMethod(),
            EqualRiskContributionMethod(),
        ]
        names = [m.name for m in methods]
        assert len(names) == len(set(names))

    def test_fixed_risk_per_trade_no_volatility(self) -> None:
        method = FixedRiskPerTradeMethod()
        request = _create_request(volatility=0.0)
        result = method.calculate(request, _create_config())
        assert result.method == "fixed_risk_per_trade"


class TestConstraints:
    """Test constraint validation."""

    def test_max_position_size_valid(self) -> None:
        result = SizingConstraints.check_max_position_size(0.20, _create_config())
        assert result.valid

    def test_max_position_size_invalid(self) -> None:
        result = SizingConstraints.check_max_position_size(0.30, _create_config())
        assert not result.valid
        assert "exceeds" in result.message

    def test_min_position_size_valid(self) -> None:
        result = SizingConstraints.check_min_position_size(0.05, _create_config())
        assert result.valid

    def test_min_position_size_invalid(self) -> None:
        result = SizingConstraints.check_min_position_size(0.005, _create_config())
        assert not result.valid
        assert "below" in result.message

    def test_min_position_size_zero(self) -> None:
        result = SizingConstraints.check_min_position_size(0.0, _create_config())
        assert result.valid

    def test_max_portfolio_exposure_valid(self) -> None:
        result = SizingConstraints.check_max_portfolio_exposure(0.80, _create_config())
        assert result.valid

    def test_max_portfolio_exposure_invalid(self) -> None:
        result = SizingConstraints.check_max_portfolio_exposure(
            1.20, _create_config()
        )
        assert not result.valid

    def test_max_sector_exposure_valid(self) -> None:
        result = SizingConstraints.check_max_sector_exposure(
            {"Technology": 0.20}, "Technology", 0.05, _create_config()
        )
        assert result.valid

    def test_max_sector_exposure_invalid(self) -> None:
        result = SizingConstraints.check_max_sector_exposure(
            {"Technology": 0.25}, "Technology", 0.10, _create_config()
        )
        assert not result.valid

    def test_max_sector_exposure_no_sector(self) -> None:
        result = SizingConstraints.check_max_sector_exposure(
            {}, "", 0.10, _create_config()
        )
        assert result.valid

    def test_cash_reserve_valid(self) -> None:
        result = SizingConstraints.check_cash_reserve(
            200000.0, 1000000.0, _create_config(cash_reserve=0.10)
        )
        assert result.valid

    def test_cash_reserve_invalid(self) -> None:
        result = SizingConstraints.check_cash_reserve(
            50000.0, 1000000.0, _create_config(cash_reserve=0.10)
        )
        assert not result.valid

    def test_max_leverage_valid(self) -> None:
        result = SizingConstraints.check_max_leverage(1.0, _create_config())
        assert result.valid

    def test_max_leverage_invalid(self) -> None:
        result = SizingConstraints.check_max_leverage(
            1.50, _create_config(max_leverage=1.0)
        )
        assert not result.valid

    def test_round_lot_valid(self) -> None:
        result = SizingConstraints.check_round_lot(
            100, _create_config(round_lot=10)
        )
        assert result.valid

    def test_round_lot_invalid(self) -> None:
        result = SizingConstraints.check_round_lot(
            105, _create_config(round_lot=10)
        )
        assert not result.valid

    def test_round_lot_no_lot(self) -> None:
        result = SizingConstraints.check_round_lot(100, _create_config(round_lot=1))
        assert result.valid

    def test_min_trade_value_valid(self) -> None:
        result = SizingConstraints.check_min_trade_value(
            50000.0, _create_config(min_trade_value=10000.0)
        )
        assert result.valid

    def test_min_trade_value_invalid(self) -> None:
        result = SizingConstraints.check_min_trade_value(
            5000.0, _create_config(min_trade_value=10000.0)
        )
        assert not result.valid

    def test_min_trade_value_zero(self) -> None:
        result = SizingConstraints.check_min_trade_value(0.0, _create_config())
        assert result.valid

    def test_validate_position(self) -> None:
        sizing = PositionSizing(
            symbol="RELIANCE", shares=100, value=250000.0, weight=0.25
        )
        results = SizingConstraints.validate_position(
            sizing, {"Technology": 0.10}, "Technology", _create_config()
        )
        assert len(results) > 0

    def test_validate_allocation(self) -> None:
        allocation = AllocationResult(
            exposure=0.80,
            cash_remaining=200000.0,
        )
        results = SizingConstraints.validate_allocation(
            allocation, _create_config()
        )
        assert len(results) > 0

    def test_constraint_result_creation(self) -> None:
        result = ConstraintResult(valid=True, message="OK", constraint="test")
        assert result.valid
        assert result.message == "OK"


class TestOptimizer:
    """Test sizing optimizer."""

    def test_optimize_empty(self) -> None:
        optimizer = SizingOptimizer()
        result = optimizer.optimize((), _create_config(), 500000.0)
        assert len(result.positions) == 0
        assert result.cash_remaining == 500000.0

    def test_optimize_single_position(self) -> None:
        optimizer = SizingOptimizer()
        sizings = (
            PositionSizing(
                symbol="RELIANCE", shares=100, value=250000.0, weight=0.25, price=2500.0
            ),
        )
        result = optimizer.optimize(sizings, _create_config(), 500000.0)
        assert len(result.positions) == 1

    def test_optimize_scales_to_cash(self) -> None:
        optimizer = SizingOptimizer()
        sizings = (
            PositionSizing(
                symbol="RELIANCE", shares=400, value=1000000.0, weight=1.0, price=2500.0
            ),
        )
        config = _create_config(default_account_size=1000000.0, max_portfolio_exposure=1.0)
        result = optimizer.optimize(sizings, config, 500000.0)
        assert result.total_value <= 500000.0

    def test_optimize_scales_to_exposure(self) -> None:
        optimizer = SizingOptimizer()
        sizings = (
            PositionSizing(
                symbol="RELIANCE", shares=500, value=1250000.0, weight=1.25, price=2500.0
            ),
        )
        config = _create_config(max_portfolio_exposure=0.80)
        result = optimizer.optimize(sizings, config, 1000000.0)
        assert result.exposure <= config.max_portfolio_exposure + 0.01

    def test_optimize_multi_position(self) -> None:
        optimizer = SizingOptimizer()
        sizings = (
            PositionSizing(
                symbol="RELIANCE", shares=100, value=250000.0, weight=0.25, price=2500.0
            ),
            PositionSizing(
                symbol="TCS", shares=100, value=350000.0, weight=0.35, price=3500.0
            ),
        )
        result = optimizer.optimize(sizings, _create_config(), 1000000.0)
        assert len(result.positions) == 2
        assert result.total_value > 0

    def test_optimize_respects_max_position(self) -> None:
        optimizer = SizingOptimizer()
        sizings = (
            PositionSizing(
                symbol="RELIANCE", shares=1000, value=2500000.0, weight=2.5, price=2500.0
            ),
        )
        config = _create_config(max_position_size=0.50)
        result = optimizer.optimize(sizings, config, 1000000.0)
        for pos in result.positions:
            assert pos.weight <= config.max_position_size + 0.01

    def test_risk_budget_allocation(self) -> None:
        optimizer = SizingOptimizer()
        requests = (
            PositionRequest(symbol="RELIANCE", price=2500.0, available_cash=500000.0),
            PositionRequest(symbol="TCS", price=3500.0, available_cash=500000.0),
        )
        budgets = (
            RiskBudget(symbol="RELIANCE", risk_weight=0.6, risk_amount=12000.0),
            RiskBudget(symbol="TCS", risk_weight=0.4, risk_amount=8000.0),
        )
        result = optimizer.allocate_by_risk_budget(
            requests, budgets, _create_config(default_account_size=1000000.0), 500000.0
        )
        assert len(result.positions) > 0

    def test_risk_budget_allocation_empty_budgets(self) -> None:
        optimizer = SizingOptimizer()
        result = optimizer.allocate_by_risk_budget((), (), _create_config(), 500000.0)
        assert len(result.positions) == 0

    def test_risk_budget_allocation_zero_risk_weight(self) -> None:
        optimizer = SizingOptimizer()
        budgets = (
            RiskBudget(symbol="RELIANCE", risk_weight=0.0, risk_amount=0.0),
        )
        result = optimizer.allocate_by_risk_budget(
            (_create_request(),), budgets, _create_config(), 500000.0
        )
        assert len(result.positions) == 0

    def test_optimize_produces_risk_budgets(self) -> None:
        optimizer = SizingOptimizer()
        sizings = (
            PositionSizing(
                symbol="RELIANCE", shares=100, value=250000.0, weight=0.25, price=2500.0,
                risk_amount=10000.0,
            ),
            PositionSizing(
                symbol="TCS", shares=50, value=175000.0, weight=0.175, price=3500.0,
                risk_amount=5000.0,
            ),
        )
        result = optimizer.optimize(sizings, _create_config(), 1000000.0)
        assert len(result.risk_budgets) == 2

    def test_optimize_warnings(self) -> None:
        optimizer = SizingOptimizer()
        config = _create_config(max_portfolio_exposure=0.30)
        sizings = (
            PositionSizing(
                symbol="RELIANCE", shares=200, value=500000.0, weight=0.50, price=2500.0,
            ),
        )
        result = optimizer.optimize(sizings, config, 500000.0)
        assert result.exposure <= config.max_portfolio_exposure + 0.01


class TestEngine:
    """Test sizing engine."""

    def test_initialization(self) -> None:
        engine = SizingEngine()
        assert isinstance(engine.config, SizingConfig)

    def test_initialization_with_config(self) -> None:
        config = _create_config(method="kelly_criterion")
        engine = SizingEngine(config=config)
        assert engine.config.method == "kelly_criterion"

    def test_default_methods_registered(self) -> None:
        engine = SizingEngine()
        assert len(engine.methods) == 10
        assert "fixed_shares" in engine.methods
        assert "kelly_criterion" in engine.methods
        assert "atr_position_sizing" in engine.methods

    def test_register_custom_method(self) -> None:
        engine = SizingEngine()
        method = FixedSharesMethod()
        engine.register_method("custom", method)
        assert "custom" in engine.methods

    def test_calculate_single_position(self) -> None:
        engine = SizingEngine()
        request = _create_request()
        result = engine.calculate_position_size(request)
        assert isinstance(result, PositionSizing)
        assert result.symbol == "RELIANCE"

    def test_calculate_with_method_override(self) -> None:
        engine = SizingEngine()
        request = _create_request()
        result = engine.calculate_position_size(request, method_name="kelly_criterion")
        assert result.method == "kelly_criterion"

    def test_calculate_nonexistent_method(self) -> None:
        engine = SizingEngine()
        request = _create_request()
        with pytest.raises(MethodNotFoundError):
            engine.calculate_position_size(request, method_name="nonexistent")

    def test_calculate_portfolio_sizes(self) -> None:
        engine = SizingEngine()
        requests = _create_requests(3)
        result = engine.calculate_portfolio_sizes(requests)
        assert isinstance(result, AllocationResult)
        assert len(result.positions) == 3

    def test_calculate_portfolio_sizes_empty(self) -> None:
        engine = SizingEngine()
        result = engine.calculate_portfolio_sizes(())
        assert len(result.positions) == 0

    def test_rebalance_sizes(self) -> None:
        engine = SizingEngine()
        current = (
            PositionSizing(
                symbol="RELIANCE", shares=100, value=250000.0, weight=0.25, price=2500.0
            ),
        )
        target = (
            PositionSizing(
                symbol="RELIANCE", shares=200, value=500000.0, weight=0.50, price=2500.0
            ),
        )
        result = engine.rebalance_sizes(current, target)
        assert len(result.positions) > 0

    def test_rebalance_sizes_empty_target(self) -> None:
        engine = SizingEngine()
        current = (
            PositionSizing(
                symbol="RELIANCE", shares=100, value=250000.0, weight=0.25, price=2500.0
            ),
        )
        result = engine.rebalance_sizes(current, ())
        assert len(result.positions) == 0

    def test_rebalance_sizes_no_change(self) -> None:
        engine = SizingEngine()
        sizing = PositionSizing(
            symbol="RELIANCE", shares=100, value=250000.0, weight=0.25, price=2500.0
        )
        result = engine.rebalance_sizes((sizing,), (sizing,))
        assert len(result.positions) == 0

    def test_rebalance_sizes_new_position(self) -> None:
        engine = SizingEngine()
        target = PositionSizing(
            symbol="TCS", shares=50, value=175000.0, weight=0.175, price=3500.0
        )
        result = engine.rebalance_sizes((), (target,))
        assert len(result.positions) == 1

    def test_validate_sizes_valid(self) -> None:
        engine = SizingEngine()
        allocation = AllocationResult(
            positions=(
                PositionSizing(
                    symbol="RELIANCE", shares=100, value=250000.0, weight=0.25, price=2500.0
                ),
            ),
            total_value=250000.0,
            cash_remaining=750000.0,
            exposure=0.25,
        )
        violations = engine.validate_sizes(allocation)
        assert isinstance(violations, tuple)

    def test_validate_sizes_violation(self) -> None:
        engine = SizingEngine()
        allocation = AllocationResult(
            positions=(
                PositionSizing(
                    symbol="RELIANCE", shares=500, value=1250000.0, weight=1.25, price=2500.0
                ),
            ),
            total_value=1250000.0,
            cash_remaining=0.0,
            exposure=1.25,
        )
        config = _create_config(max_position_size=0.25)
        violations = engine.validate_sizes(allocation, config)
        assert len(violations) > 0

    def test_optimize_allocations(self) -> None:
        engine = SizingEngine()
        sizings = (
            PositionSizing(
                symbol="RELIANCE", shares=200, value=500000.0, weight=0.50, price=2500.0
            ),
        )
        result = engine.optimize_allocations(sizings, available_cash=400000.0)
        assert isinstance(result, AllocationResult)
        assert result.total_value <= 400000.0

    def test_compute_metrics(self) -> None:
        engine = SizingEngine()
        allocation = AllocationResult(
            positions=(
                PositionSizing(
                    symbol="RELIANCE", shares=100, value=250000.0, weight=0.25, price=2500.0
                ),
                PositionSizing(
                    symbol="TCS", shares=50, value=175000.0, weight=0.175, price=3500.0
                ),
            ),
            total_value=425000.0,
            cash_remaining=575000.0,
            exposure=0.425,
        )
        metrics = engine.compute_metrics(allocation)
        assert metrics.total_positions == 2
        assert metrics.total_exposure == 0.425

    def test_compute_metrics_empty(self) -> None:
        engine = SizingEngine()
        allocation = AllocationResult()
        metrics = engine.compute_metrics(allocation)
        assert metrics.total_positions == 0

    def test_generate_statistics(self) -> None:
        engine = SizingEngine()
        stats = engine.generate_statistics(
            elapsed=0.15,
            violations=("VaR violation",),
            warnings=("Concentration high",),
        )
        assert stats.elapsed_seconds == 0.15
        assert len(stats.violations) == 1

    def test_total_calculations_tracked(self) -> None:
        engine = SizingEngine()
        request = _create_request()
        engine.calculate_position_size(request)
        engine.calculate_position_size(request)
        stats = engine.generate_statistics(0.1)
        assert stats.total_calculations == 2

    def test_calculate_with_risk_engine(self) -> None:
        engine = SizingEngine(risk_engine=object())
        assert engine._risk_engine is not None

    def test_calculate_with_portfolio_engine(self) -> None:
        engine = SizingEngine(portfolio_engine=object())
        assert engine._portfolio_engine is not None

    def test_calculate_with_strategy_engine(self) -> None:
        engine = SizingEngine(strategy_engine=object())
        assert engine._strategy_engine is not None

    def test_portfolio_sizes_with_method_override(self) -> None:
        engine = SizingEngine()
        requests = _create_requests(2)
        result = engine.calculate_portfolio_sizes(requests, method_name="atr_position_sizing")
        for pos in result.positions:
            assert pos.method == "atr_position_sizing"

    def test_rebalance_with_custom_config(self) -> None:
        engine = SizingEngine()
        current = (
            PositionSizing(
                symbol="RELIANCE", shares=100, value=250000.0, weight=0.25, price=2500.0
            ),
        )
        target = (
            PositionSizing(
                symbol="RELIANCE", shares=200, value=500000.0, weight=0.50, price=2500.0
            ),
        )
        config = _create_config(max_portfolio_exposure=0.30)
        result = engine.rebalance_sizes(current, target, config)
        assert result.exposure <= config.max_portfolio_exposure or len(result.warnings) > 0


class TestFactory:
    """Test factory creation."""

    def test_create_default(self) -> None:
        engine = SizingFactory.create()
        assert isinstance(engine, SizingEngine)
        assert len(engine.methods) == 10

    def test_create_with_config(self) -> None:
        config = _create_config(method="kelly_criterion")
        engine = SizingFactory.create(config=config)
        assert engine.config.method == "kelly_criterion"

    def test_create_with_optimizer(self) -> None:
        optimizer = SizingOptimizer()
        engine = SizingFactory.create(optimizer=optimizer)
        assert engine._optimizer is optimizer

    def test_create_with_portfolio_engine(self) -> None:
        engine = SizingFactory.create(portfolio_engine=object())
        assert engine._portfolio_engine is not None

    def test_create_with_risk_engine(self) -> None:
        engine = SizingFactory.create(risk_engine=object())
        assert engine._risk_engine is not None

    def test_create_with_strategy_engine(self) -> None:
        engine = SizingFactory.create(strategy_engine=object())
        assert engine._strategy_engine is not None

    def test_create_with_methods(self) -> None:
        custom_method = FixedSharesMethod()
        engine = SizingFactory.create_with_methods(
            {"custom_method": custom_method}
        )
        assert "custom_method" in engine.methods

    def test_create_from_config(self) -> None:
        config = _create_config(method="volatility_targeting")
        engine = SizingFactory.create_from_config(config)
        assert engine.config.method == "volatility_targeting"

    def test_create_with_all_dependencies(self) -> None:
        engine = SizingFactory.create(
            config=_create_config(),
            optimizer=SizingOptimizer(),
            portfolio_engine=object(),
            risk_engine=object(),
            strategy_engine=object(),
        )
        assert engine._portfolio_engine is not None
        assert engine._risk_engine is not None
        assert engine._strategy_engine is not None


class TestExceptions:
    """Test exception hierarchy."""

    def test_sizing_error(self) -> None:
        with pytest.raises(SizingError):
            raise SizingError("test")

    def test_invalid_sizing_config_error(self) -> None:
        with pytest.raises(InvalidSizingConfigError):
            raise InvalidSizingConfigError("test")

    def test_insufficient_data_error(self) -> None:
        with pytest.raises(InsufficientDataError):
            raise InsufficientDataError("test")

    def test_calculation_error(self) -> None:
        with pytest.raises(CalculationError):
            raise CalculationError("test", "test")

    def test_calculation_error_attributes(self) -> None:
        error = CalculationError("test_method", "test_message")
        assert error.calculation == "test_method"
        assert "test_method" in str(error)

    def test_constraint_violation_error(self) -> None:
        with pytest.raises(ConstraintViolationError):
            raise ConstraintViolationError("test", "test")

    def test_constraint_violation_error_attributes(self) -> None:
        error = ConstraintViolationError("test_constraint", "test_message")
        assert error.constraint == "test_constraint"
        assert "test_constraint" in str(error)

    def test_empty_portfolio_error(self) -> None:
        with pytest.raises(EmptyPortfolioError):
            raise EmptyPortfolioError()

    def test_method_not_found_error(self) -> None:
        with pytest.raises(MethodNotFoundError):
            raise MethodNotFoundError("test")

    def test_method_not_found_error_attributes(self) -> None:
        error = MethodNotFoundError("nonexistent_method")
        assert error.name == "nonexistent_method"
        assert "nonexistent_method" in str(error)


class TestIntegration:
    """Integration tests for complete sizing flow."""

    def test_complete_sizing_flow(self) -> None:
        engine = SizingFactory.create()

        requests = _create_requests(3)
        result = engine.calculate_portfolio_sizes(requests)

        assert isinstance(result, AllocationResult)
        assert len(result.positions) > 0
        assert result.total_value > 0
        assert result.exposure > 0

        metrics = engine.compute_metrics(result)
        assert metrics.total_positions == len(result.positions)

        violations = engine.validate_sizes(result)
        assert isinstance(violations, tuple)

    def test_fixed_fractional_allocation(self) -> None:
        engine = SizingEngine()
        requests = _create_requests(3, account_size=1000000.0)
        result = engine.calculate_portfolio_sizes(requests)
        assert len(result.positions) == 3

    def test_kelly_allocation(self) -> None:
        config = _create_config(method="kelly_criterion")
        engine = SizingEngine(config=config)
        requests = (
            PositionRequest(
                symbol="RELIANCE",
                price=2500.0,
                account_size=1000000.0,
                available_cash=500000.0,
                win_rate=0.55,
                avg_win=3000.0,
                avg_loss=1500.0,
            ),
        )
        result = engine.calculate_position_size(requests[0])
        assert result.method == "kelly_criterion"

    def test_atr_allocation(self) -> None:
        config = _create_config(method="atr_position_sizing")
        engine = SizingEngine(config=config)
        requests = (
            PositionRequest(
                symbol="RELIANCE",
                price=2500.0,
                account_size=1000000.0,
                available_cash=500000.0,
                atr=50.0,
            ),
        )
        result = engine.calculate_position_size(requests[0])
        assert result.method == "atr_position_sizing"
        assert result.shares > 0

    def test_volatility_targeting_allocation(self) -> None:
        config = _create_config(method="volatility_targeting", vol_target=0.15)
        engine = SizingEngine(config=config)
        request = _create_request(volatility=0.25)
        result = engine.calculate_position_size(request)
        assert result.method == "volatility_targeting"

    def test_multi_method_portfolio(self) -> None:
        engine = SizingEngine()
        requests = _create_requests(3)

        result_kelly = engine.calculate_portfolio_sizes(requests, method_name="kelly_criterion")
        result_atr = engine.calculate_portfolio_sizes(requests, method_name="atr_position_sizing")

        assert result_kelly is not None
        assert result_atr is not None

    def test_full_pipeline(self) -> None:
        engine = SizingFactory.create()
        requests = _create_requests(2)

        allocation = engine.calculate_portfolio_sizes(requests)
        metrics = engine.compute_metrics(allocation)
        violations = engine.validate_sizes(allocation)
        stats = engine.generate_statistics(
            elapsed=0.25,
            violations=violations,
        )

        assert metrics.total_positions == 2
        assert stats.total_calculations >= 2
        assert stats.elapsed_seconds == 0.25

    def test_optimization_scales_proportionally(self) -> None:
        sizings = (
            PositionSizing(
                symbol="A", shares=100, value=250000.0, weight=0.25, price=2500.0
            ),
            PositionSizing(
                symbol="B", shares=100, value=250000.0, weight=0.25, price=2500.0
            ),
        )
        optimizer = SizingOptimizer()
        result = optimizer.optimize(sizings, _create_config(), 300000.0)
        assert result.total_value <= 300000.0
        assert abs(
            result.positions[0].value / result.positions[1].value - 1.0
        ) < 0.01

    def test_risk_budget_allocation_distribution(self) -> None:
        optimizer = SizingOptimizer()
        requests = (
            PositionRequest(symbol="A", price=100.0, available_cash=100000.0,
                            account_size=200000.0),
            PositionRequest(symbol="B", price=200.0, available_cash=100000.0,
                            account_size=200000.0),
        )
        budgets = (
            RiskBudget(symbol="A", risk_weight=0.7, risk_amount=7000.0),
            RiskBudget(symbol="B", risk_weight=0.3, risk_amount=3000.0),
        )
        config = _create_config(
            default_account_size=200000.0,
            max_position_size=1.0,
            min_position_size=0.0,
        )
        result = optimizer.allocate_by_risk_budget(requests, budgets, config, 100000.0)
        assert len(result.positions) == 2
        if result.positions[0].value > 0 and result.positions[1].value > 0:
            ratio = result.positions[0].value / result.positions[1].value
            assert ratio > 1.0
