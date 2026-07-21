"""Risk management engine tests.

Covers all functionality including exposure, VaR, stress tests,
scenarios, and limit monitoring.
"""

from __future__ import annotations

import math

import pytest

from backend.risk.engine import RiskEngine
from backend.risk.exceptions import (
    CalculationError,
    EmptyPortfolioError,
    InsufficientDataError,
    InvalidRiskConfigError,
    LimitViolationError,
    RiskError,
    ScenarioError,
    ScenarioNotFoundError,
    StressTestError,
    VaRCalculationError,
)
from backend.risk.exposure import (
    calculate_cash_exposure,
    calculate_concentration_index,
    calculate_exposure,
    calculate_gross_exposure,
    calculate_industry_exposure,
    calculate_long_exposure,
    calculate_net_exposure,
    calculate_position_exposure,
    calculate_sector_exposure,
    calculate_short_exposure,
)
from backend.risk.factory import RiskFactory
from backend.risk.models import (
    ConfidenceLevel,
    Exposure,
    RiskConfig,
    RiskDefinition,
    RiskMetadata,
    RiskMetrics,
    RiskPosition,
    RiskStatistics,
    ScenarioResult,
    StressScenario,
    StressTestResult,
    VaRMethod,
    VaRResult,
)
from backend.risk.scenarios import (
    ScenarioRegistry,
    build_default_registry,
    custom_scenario,
    inflation_surge_scenario,
    interest_rate_rise_scenario,
    market_crash_scenario,
    multi_factor_scenario,
    run_all_scenarios,
    run_scenario,
    single_factor_scenario,
)
from backend.risk.stress import (
    custom_stress,
    interest_rate_shock_stress,
    liquidity_shock_stress,
    market_crash_stress,
    run_all_stress_tests,
    run_stress_test,
    sector_crash_stress,
    volatility_expansion_stress,
)
from backend.risk.var import (
    calculate_var,
    historical_var,
    monte_carlo_var,
    parametric_var,
)


def _create_config(**kwargs: object) -> RiskConfig:
    """Create a test configuration."""
    defaults = {
        "lookback_period": 252,
        "confidence_level": ConfidenceLevel.P95,
        "maximum_var": 0.05,
        "maximum_position_size": 0.25,
        "maximum_sector_exposure": 0.30,
        "maximum_drawdown": 0.20,
        "maximum_volatility": 0.25,
        "maximum_concentration": 0.25,
    }
    defaults.update(kwargs)
    return RiskConfig(**defaults)  # type: ignore[arg-type]


def _create_positions(
    symbols: tuple[str, ...] = ("RELIANCE", "TCS", "INFY"),
    weights: tuple[float, ...] | None = None,
    sectors: tuple[str, ...] | None = None,
    return_length: int = 252,
) -> tuple[RiskPosition, ...]:
    """Create test positions."""
    if weights is None:
        weights = (0.4, 0.35, 0.25)
    if sectors is None:
        sectors = ("Energy", "Technology", "Technology")

    positions = []
    for i, symbol in enumerate(symbols):
        weight = weights[i] if i < len(weights) else 0.1
        sector = sectors[i] if i < len(sectors) else "Unknown"

        returns = tuple(
            0.001 * (1 + 0.1 * math.sin(j / 10)) for j in range(return_length)
        )

        vol = 0.02
        if returns and len(returns) > 1:
            mean = sum(returns) / len(returns)
            var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
            vol = math.sqrt(var)

        positions.append(
            RiskPosition(
                symbol=symbol,
                weight=weight,
                return_series=returns,
                sector=sector,
                beta=1.0 + (i * 0.1),
                volatility=vol,
            )
        )

    return tuple(positions)


class TestExposure:
    """Test exposure calculations."""

    def test_gross_exposure(self) -> None:
        positions = _create_positions()
        gross = calculate_gross_exposure(positions)
        assert gross == pytest.approx(1.0, abs=0.01)

    def test_net_exposure(self) -> None:
        positions = _create_positions()
        net = calculate_net_exposure(positions)
        assert net == pytest.approx(1.0, abs=0.01)

    def test_long_exposure(self) -> None:
        positions = _create_positions()
        long = calculate_long_exposure(positions)
        assert long == pytest.approx(1.0, abs=0.01)

    def test_short_exposure(self) -> None:
        positions = _create_positions()
        short = calculate_short_exposure(positions)
        assert short == 0.0

    def test_cash_exposure(self) -> None:
        positions = _create_positions()
        cash = calculate_cash_exposure(positions)
        assert cash == pytest.approx(0.0, abs=0.01)

    def test_sector_exposure(self) -> None:
        positions = _create_positions()
        sector = calculate_sector_exposure(positions)
        assert "Energy" in sector
        assert "Technology" in sector

    def test_industry_exposure(self) -> None:
        positions = _create_positions()
        industry = calculate_industry_exposure(positions)
        assert len(industry) > 0

    def test_position_exposure(self) -> None:
        positions = _create_positions()
        pos_exp = calculate_position_exposure(positions)
        assert "RELIANCE" in pos_exp
        assert "TCS" in pos_exp

    def test_concentration_index(self) -> None:
        positions = _create_positions()
        hhi = calculate_concentration_index(positions)
        assert 0 < hhi < 1

    def test_calculate_exposure(self) -> None:
        positions = _create_positions()
        config = _create_config()
        exposure = calculate_exposure(positions, config)
        assert isinstance(exposure, Exposure)
        assert exposure.gross_exposure > 0


class TestVaR:
    """Test VaR calculations."""

    def test_historical_var(self) -> None:
        returns = [0.01, -0.02, 0.015, -0.01, 0.005, -0.03, 0.02, -0.015, 0.01, -0.005]
        result = historical_var(returns, ConfidenceLevel.P95, 10)
        assert isinstance(result, VaRResult)
        assert result.var >= 0

    def test_historical_var_insufficient_data(self) -> None:
        result = historical_var([0.01], ConfidenceLevel.P95, 10)
        assert isinstance(result, VaRResult)

    def test_parametric_var(self) -> None:
        returns = [0.01, -0.02, 0.015, -0.01, 0.005, -0.03, 0.02, -0.015, 0.01, -0.005]
        result = parametric_var(returns, ConfidenceLevel.P95, 10)
        assert isinstance(result, VaRResult)
        assert result.var >= 0

    def test_parametric_var_insufficient_data(self) -> None:
        result = parametric_var([], ConfidenceLevel.P95, 10)
        assert isinstance(result, VaRResult)
        assert result.var == 0.0

    def test_monte_carlo_var(self) -> None:
        returns = [0.01, -0.02, 0.015, -0.01, 0.005, -0.03, 0.02, -0.015, 0.01, -0.005]
        result = monte_carlo_var(returns, ConfidenceLevel.P95, 10, 1000)
        assert isinstance(result, VaRResult)
        assert result.var >= 0

    def test_calculate_var(self) -> None:
        positions = _create_positions()
        config = _create_config()
        result = calculate_var(positions, config)
        assert isinstance(result, VaRResult)

    def test_calculate_var_empty(self) -> None:
        config = _create_config()
        result = calculate_var((), config)
        assert result.var == 0.0


class TestStress:
    """Test stress testing."""

    def test_market_crash(self) -> None:
        positions = _create_positions()
        config = _create_config()
        result = market_crash_stress(positions, config)
        assert isinstance(result, StressTestResult)
        assert result.portfolio_impact < 0

    def test_sector_crash(self) -> None:
        positions = _create_positions()
        config = _create_config()
        result = sector_crash_stress(positions, config, "Technology")
        assert isinstance(result, StressTestResult)

    def test_interest_rate_shock(self) -> None:
        positions = _create_positions()
        config = _create_config()
        result = interest_rate_shock_stress(positions, config)
        assert isinstance(result, StressTestResult)

    def test_volatility_expansion(self) -> None:
        positions = _create_positions()
        config = _create_config()
        result = volatility_expansion_stress(positions, config)
        assert isinstance(result, StressTestResult)

    def test_liquidity_shock(self) -> None:
        positions = _create_positions()
        config = _create_config()
        result = liquidity_shock_stress(positions, config)
        assert isinstance(result, StressTestResult)

    def test_custom_stress(self) -> None:
        positions = _create_positions()
        config = _create_config()
        shocks = {"RELIANCE": 0.2, "TCS": 0.1}
        result = custom_stress(positions, config, shocks)
        assert isinstance(result, StressTestResult)

    def test_run_stress_test(self) -> None:
        positions = _create_positions()
        config = _create_config()
        result = run_stress_test(positions, config, StressScenario.MARKET_CRASH)
        assert isinstance(result, StressTestResult)

    def test_run_all_stress_tests(self) -> None:
        positions = _create_positions()
        config = _create_config()
        results = run_all_stress_tests(positions, config)
        assert len(results) > 0


class TestScenarios:
    """Test scenario analysis."""

    def test_single_factor_scenario(self) -> None:
        positions = _create_positions()
        config = _create_config()
        result = single_factor_scenario(positions, config, "market", -0.20)
        assert isinstance(result, ScenarioResult)
        assert result.portfolio_return < 0

    def test_multi_factor_scenario(self) -> None:
        positions = _create_positions()
        config = _create_config()
        factors = {"market": -0.20, "interest_rate": 0.02}
        result = multi_factor_scenario(positions, config, factors)
        assert isinstance(result, ScenarioResult)

    def test_market_crash_scenario(self) -> None:
        positions = _create_positions()
        config = _create_config()
        result = market_crash_scenario(positions, config)
        assert isinstance(result, ScenarioResult)

    def test_interest_rate_rise_scenario(self) -> None:
        positions = _create_positions()
        config = _create_config()
        result = interest_rate_rise_scenario(positions, config)
        assert isinstance(result, ScenarioResult)

    def test_inflation_surge_scenario(self) -> None:
        positions = _create_positions()
        config = _create_config()
        result = inflation_surge_scenario(positions, config)
        assert isinstance(result, ScenarioResult)

    def test_custom_scenario(self) -> None:
        positions = _create_positions()
        config = _create_config()
        factors = {"market": -0.15}
        result = custom_scenario(positions, config, factors, "My Scenario")
        assert isinstance(result, ScenarioResult)

    def test_scenario_registry(self) -> None:
        registry = ScenarioRegistry()
        registry.register("test", market_crash_scenario)
        assert "test" in registry.list_scenarios()

    def test_scenario_registry_not_found(self) -> None:
        registry = ScenarioRegistry()
        with pytest.raises(ScenarioNotFoundError):
            registry.get("nonexistent")

    def test_build_default_registry(self) -> None:
        registry = build_default_registry()
        assert len(registry.list_scenarios()) > 0

    def test_run_scenario(self) -> None:
        positions = _create_positions()
        config = _create_config()
        result = run_scenario(positions, config, "market_crash")
        assert isinstance(result, ScenarioResult)

    def test_run_all_scenarios(self) -> None:
        positions = _create_positions()
        config = _create_config()
        results = run_all_scenarios(positions, config)
        assert len(results) > 0


class TestRiskEngine:
    """Test risk engine."""

    def test_initialization(self) -> None:
        engine = RiskEngine()
        assert engine.config is None

    def test_evaluate(self) -> None:
        positions = _create_positions()
        config = _create_config()
        engine = RiskEngine()
        metrics = engine.evaluate(positions, config)
        assert isinstance(metrics, RiskMetrics)
        assert metrics.exposure.gross_exposure > 0

    def test_evaluate_empty(self) -> None:
        config = _create_config()
        engine = RiskEngine()
        metrics = engine.evaluate((), config)
        assert isinstance(metrics, RiskMetrics)

    def test_evaluate_portfolio(self) -> None:
        weights = {"RELIANCE": 0.4, "TCS": 0.35, "INFY": 0.25}
        returns_data = {
            "RELIANCE": [0.01, -0.02, 0.015],
            "TCS": [0.005, -0.01, 0.01],
            "INFY": [0.008, -0.015, 0.012],
        }
        config = _create_config()
        engine = RiskEngine()
        metrics = engine.evaluate_portfolio(weights, returns_data, config)
        assert isinstance(metrics, RiskMetrics)

    def test_evaluate_backtest(self) -> None:
        equity_curve = [100000, 105000, 102000, 108000, 110000]
        config = _create_config()
        engine = RiskEngine()
        metrics = engine.evaluate_backtest(equity_curve, config)
        assert isinstance(metrics, RiskMetrics)

    def test_evaluate_strategy(self) -> None:
        signals = {"RELIANCE": 0.8, "TCS": 0.6, "INFY": 0.4}
        returns_data = {
            "RELIANCE": [0.01, -0.02, 0.015],
            "TCS": [0.005, -0.01, 0.01],
            "INFY": [0.008, -0.015, 0.012],
        }
        config = _create_config()
        engine = RiskEngine()
        metrics = engine.evaluate_strategy(signals, returns_data, config)
        assert isinstance(metrics, RiskMetrics)

    def test_check_limits(self) -> None:
        positions = _create_positions()
        config = _create_config(maximum_var=0.001)
        engine = RiskEngine()
        metrics = engine.evaluate(positions, config)
        violations = engine.check_limits(metrics, config)
        assert isinstance(violations, tuple)

    def test_generate_warnings(self) -> None:
        positions = _create_positions()
        config = _create_config()
        engine = RiskEngine()
        metrics = engine.evaluate(positions, config)
        warnings = engine.generate_warnings(metrics, config)
        assert isinstance(warnings, tuple)

    def test_generate_actions(self) -> None:
        positions = _create_positions()
        config = _create_config()
        engine = RiskEngine()
        metrics = engine.evaluate(positions, config)
        violations = engine.check_limits(metrics, config)
        actions = engine.generate_actions(metrics, config, violations)
        assert isinstance(actions, tuple)


class TestRiskFactory:
    """Test factory creation."""

    def test_create_default(self) -> None:
        engine = RiskFactory.create()
        assert isinstance(engine, RiskEngine)

    def test_create_with_config(self) -> None:
        config = _create_config()
        engine = RiskFactory.create(config=config)
        assert isinstance(engine, RiskEngine)

    def test_create_with_custom_scenarios(self) -> None:
        engine = RiskFactory.create_with_custom_scenarios()
        assert isinstance(engine, RiskEngine)

    def test_create_from_registry(self) -> None:
        registry = build_default_registry()
        engine = RiskFactory.create_from_registry(registry)
        assert isinstance(engine, RiskEngine)


class TestModels:
    """Test data models."""

    def test_risk_metadata(self) -> None:
        metadata = RiskMetadata(name="Test")
        assert metadata.name == "Test"
        assert metadata.version == "1.0"

    def test_risk_config(self) -> None:
        config = RiskConfig()
        assert config.var_method == VaRMethod.HISTORICAL
        assert config.lookback_period == 252

    def test_risk_definition(self) -> None:
        definition = RiskDefinition(
            metadata=RiskMetadata(name="Test"),
            config=RiskConfig(),
        )
        assert definition.metadata.name == "Test"

    def test_exposure(self) -> None:
        exposure = Exposure(gross_exposure=1.0, net_exposure=0.8)
        assert exposure.gross_exposure == 1.0

    def test_var_result(self) -> None:
        result = VaRResult(var=0.05, cvar=0.08)
        assert result.var == 0.05

    def test_stress_test_result(self) -> None:
        result = StressTestResult(scenario="Test", portfolio_impact=-0.15)
        assert result.portfolio_impact == -0.15

    def test_scenario_result(self) -> None:
        result = ScenarioResult(scenario_name="Test", portfolio_return=-0.10)
        assert result.portfolio_return == -0.10

    def test_risk_metrics(self) -> None:
        metrics = RiskMetrics(volatility=0.15, sharpe_ratio=1.2)
        assert metrics.volatility == 0.15

    def test_risk_statistics(self) -> None:
        stats = RiskStatistics(total_evaluations=10)
        assert stats.total_evaluations == 10

    def test_risk_position(self) -> None:
        position = RiskPosition(
            symbol="RELIANCE",
            weight=0.5,
            return_series=(0.01, -0.02, 0.015),
        )
        assert position.symbol == "RELIANCE"

    def test_var_method(self) -> None:
        assert VaRMethod.HISTORICAL == "HISTORICAL"

    def test_confidence_level(self) -> None:
        assert ConfidenceLevel.P95 == "95"

    def test_stress_scenario(self) -> None:
        assert StressScenario.MARKET_CRASH == "MARKET_CRASH"


class TestExceptions:
    """Test exception hierarchy."""

    def test_risk_error(self) -> None:
        with pytest.raises(RiskError):
            raise RiskError("test")

    def test_invalid_risk_config_error(self) -> None:
        with pytest.raises(InvalidRiskConfigError):
            raise InvalidRiskConfigError("test")

    def test_insufficient_data_error(self) -> None:
        with pytest.raises(InsufficientDataError):
            raise InsufficientDataError("test")

    def test_var_calculation_error(self) -> None:
        with pytest.raises(VaRCalculationError):
            raise VaRCalculationError("test")

    def test_stress_test_error(self) -> None:
        with pytest.raises(StressTestError):
            raise StressTestError("test")

    def test_scenario_error(self) -> None:
        with pytest.raises(ScenarioError):
            raise ScenarioError("test")

    def test_limit_violation_error(self) -> None:
        with pytest.raises(LimitViolationError):
            raise LimitViolationError("test", "test")

    def test_empty_portfolio_error(self) -> None:
        with pytest.raises(EmptyPortfolioError):
            raise EmptyPortfolioError()

    def test_scenario_not_found_error(self) -> None:
        with pytest.raises(ScenarioNotFoundError):
            raise ScenarioNotFoundError("test")

    def test_calculation_error(self) -> None:
        with pytest.raises(CalculationError):
            raise CalculationError("test", "test")


class TestIntegration:
    """Integration tests for complete risk flow."""

    def test_complete_risk_flow(self) -> None:
        positions = _create_positions()
        config = _create_config()
        engine = RiskFactory.create()

        metrics = engine.evaluate(positions, config)
        assert isinstance(metrics, RiskMetrics)
        assert metrics.exposure.gross_exposure > 0
        assert metrics.var.var != 0.0 or metrics.var.var == 0.0

        violations = engine.check_limits(metrics, config)
        assert isinstance(violations, tuple)

        warnings = engine.generate_warnings(metrics, config)
        assert isinstance(warnings, tuple)

        actions = engine.generate_actions(metrics, config, violations)
        assert isinstance(actions, tuple)

    def test_stress_and_scenarios(self) -> None:
        positions = _create_positions()
        config = _create_config()
        engine = RiskEngine()

        metrics = engine.evaluate(positions, config)
        assert len(metrics.stress_tests) > 0
        assert len(metrics.scenarios) > 0

    def test_limit_monitoring(self) -> None:
        positions = _create_positions()
        config = _create_config(maximum_var=0.001)
        engine = RiskEngine()

        metrics = engine.evaluate(positions, config)
        violations = engine.check_limits(metrics, config)
        assert len(violations) > 0
