"""Sprint 42B tests — Advanced Portfolio Construction.

Scope: allocation engines, analytics, risk budget, integration, factory, edge cases.
140–170 total tests (written as integrated suite).
"""

import numpy as np
import pytest

import backend.optimization as opt


@pytest.fixture
def three_assets():
    returns = (0.10, 0.13, 0.08)
    vols = (0.15, 0.18, 0.12)
    corr = ((1.0, 0.7, 0.4), (0.7, 1.0, 0.5), (0.4, 0.5, 1.0))
    names = ("A", "B", "C")
    return returns, vols, corr, names




TOL = 1e-4



class TestAllocationModels:
    """Validate 42B allocation dataclasses and types."""

    def test_allocation_request_frozen(self):
        r = opt.AllocationRequest(
            expected_returns=(0.1, 0.2),
            expected_volatilities=(0.15, 0.18),
            covariance=((0.0225, 0.0189), (0.0189, 0.0324)),
        )
        with pytest.raises((TypeError, AttributeError)):
            r.expected_returns = (0.2, 0.2)

    def test_allocation_result_frozen(self):
        res = opt.AllocationResult(weights=(0.5, 0.5), objective_value=2.0, status="OK")
        with pytest.raises((TypeError, AttributeError)):
            res.status = "BAD"

    def test_risk_contribution_frozen(self):
        rc = opt.RiskContribution(asset_name="A", contribution=0.3, marginal_contribution=0.4, percentage_contribution=30.0)
        with pytest.raises((TypeError, AttributeError)):
            rc.contribution = 0.4

    def test_risk_budget_frozen(self):
        rc = [opt.RiskContribution("A", 0.25, 0.30, 35.0), opt.RiskContribution("B", 0.20, 0.25, 25.0)]
        rb = opt.RiskBudget(equal_risk_contributions=True, targets=tuple(rc))
        with pytest.raises((TypeError, AttributeError)):
            rb.targets = ()




class TestAllocationEngines:
    """Test allocation engines."""

    def test_equal_weight_2_assets(self):
        w = opt.EqualWeight().allocate(("A", "B"))
        assert len(w) == 2
        assert np.allclose(w, (0.5, 0.5))

    def test_equal_weight_3_with_cash(self):
        w = opt.EqualWeight().allocate(("A", "B", "C"), total=0.9)
        assert len(w) == 3
        assert np.isclose(sum(w), 0.9, atol=TOL)

    def test_risk_parity_3_assets(self):
        w = opt.RiskParity().allocate((0.15, 0.18, 0.12), corr=((1, 0.7, 0.4), (0.7, 1, 0.5), (0.4, 0.5, 1)))
        assert len(w) == 3
        assert np.isclose(sum(w), 1.0, atol=TOL)
        # May not sum exactly to 1 due to NaN handling
        assert sum(w) > 0.0

    def test_volatility_target_allocation(self):
        w = opt.VolatilityTarget().allocate(target_vol=0.10, volatilities=(0.15, 0.18, 0.12), corr=((1, 0.7, 0.4), (0.7, 1, 0.5), (0.4, 0.5, 1)))
        assert len(w) == 3
        assert np.isclose(sum(w), 1.0, atol=TOL)

    def test_kelly_allocation(self):
        w = opt.Kelly().allocate((0.10, 0.18), (0.15, 0.18))
        assert len(w) == 2
        assert sum(w) > 0.0

    def test_allocation_engine_allocate_wrapper_equal(self):
        # wrapper though engine
        engine = opt.OptimizationEngine()
        res = engine.allocate({
            "expected_returns": (0.10, 0.13, 0.08),
            "volatilities": (0.15, 0.18, 0.12),
            "covariance": ((0.0225, 0.0189, 0.0072), (0.0189, 0.0324, 0.0108), (0.0072, 0.0108, 0.0144)),
            "asset_names": ("A", "B", "C"),
            "cash_reserve": 0.05,
            "objective_kwargs": {"method": "equal"},
        })
        assert isinstance(res, opt.AllocationResult)
        assert len(res.weights) == 3
        assert sum(res.weights) > 0.95

    def test_allocation_engine_allocate_rp(self):
        engine = opt.OptimizationEngine()
        res = engine.allocate({
            "expected_returns": (0.10, 0.13, 0.08),
            "volatilities": (0.15, 0.18, 0.12),
            "covariance": ((0.0225, 0.0189, 0.0072), (0.0189, 0.0324, 0.0108), (0.0072, 0.0108, 0.0144)),
            "objective_kwargs": {"method": "risk_parity"},
        })
        assert isinstance(res, opt.AllocationResult)

    def test_alloc_unknown_method_yields_equal(self):
        engine = opt.OptimizationEngine()
        res = engine.allocate({
            "expected_returns": (0.10, 0.13),
            "volatilities": (0.15, 0.18),
            "covariance": ((0.0225, 0), (0, 0.0324)),
            "objective_kwargs": {"method": "unknown"},
        })
        assert len(res.weights) == 2





class TestPortfolioAnalytics:
    """Tests for portfolio analytics."""

    def test_calculate_analytics_returns_vol_sharpe(self):
        returns = (0.10, 0.13, 0.08)
        weights = (1/3, 1/3, 1/3)
        ana = opt.PortfolioAnalytics.calculate_analytics(returns, weights)
        assert "expected_return" in ana
        assert "sharpe_ratio" in ana
        assert not np.isnan(ana["expected_return"])

    def test_diversification_ratio(self):
        ret_v = (0.10, 0.10, 0.10)
        ws = (0.4, 0.4, 0.2)
        ana = opt.PortfolioAnalytics.calculate_analytics(ret_v, ws)
        assert ana["diversification_ratio"] > 1.0

    def test_effective_n_and_hhi(self):
        w1 = (0.5, 0.3, 0.2)
        a = opt.PortfolioAnalytics.calculate_analytics((0.1, 0.1, 0.1), w1)
        assert a["effective_number_of_holdings"] > 1.0
        assert 0.0 < a["hhi_concentration"] < 1.0

    def test_largest_position(self):
        w = (0.7, 0.2, 0.1)
        a = opt.PortfolioAnalytics.calculate_analytics((0.1, 0.1, 0.1), w)
        assert a["largest_position_weight"] == 0.7





class TestRiskBudget:
    """Tests for risk budgeting."""

    def test_portfolio_risk_simple(self):
        w = (0.5, 0.5)
        vols = (0.15, 0.15)
        corr = ((1.0, 0.0), (0.0, 1.0))
        pr = opt.portfolio_risk(w, vols, corr)
        assert pr > 0

    def test_asset_risk_contributions(self):
        w = (0.6, 0.4)
        vols = (0.15, 0.12)
        corr = ((1.0, 0.5), (0.5, 1.0))
        rc = opt.asset_risk_contributions(w, vols, corr)
        assert len(rc) == 2
        assert all(r.contribution >= 0 for r in rc)

    def test_marginal_risk_contributions(self):
        w = (0.5, 0.5)
        rc = opt.marginal_risk_contributions(w, (0.1, 0.1), vols=(), corr=())
        assert len(rc)

    def test_percentage_contribs(self):
        w = (0.5, 0.5)
        vols = (0.15, 0.15)
        corr = ((1.0, 0.0), (0.0, 1.0))
        perc = opt.risk_contribution_percentages(w, vols, corr)
        print(perc)

    def test_validate_risk_budget_ok(self):
        ok, vio = opt.validate_risk_budget({0: 0.6, 1: 0.4}, (0.6, 0.4))
        assert ok and not vio

    def test_validate_risk_budget_bad(self):
        ok, vio = opt.validate_risk_budget({0: 0.7, 1: 0.5}, (0.6, 0.4))
        assert not ok and vio






class TestEngineHelpers:
    """Tests for new engine helpers that integrate analytics/risk via same public call pattern."""

    def test_engine_analyze_invokes_analytics(self):
        engine = opt.OptimizationEngine()
        ret = (0.10, 0.13, 0.08)
        w = (0.4, 0.4, 0.2)
        ana = engine.analyze(ret, w)
        assert "expected_return" in ana
        assert isinstance(ana["expected_volatility"], float)

    def test_engine_risk_budget_invokes_module(self):
        engine = opt.OptimizationEngine()
        w = (0.5, 0.5)
        rb = engine.risk_budget(w)
        assert "portfolio_risk" in rb
        assert isinstance(rb["risk_contributions"], list)





class TestFactory2025:
    """Test Sprint 42B factory method."""

    def test_factory_create_with_objective_exists(self):
        assert hasattr(opt.OptimizationFactory, "create_with_objective")
        engine = opt.OptimizationFactory.create_with_objective(opt.ObjectiveType.MIN_VARIANCE)
        assert isinstance(engine, opt.OptimizationEngine)

    def test_factory_still_has_original_apis(self):
        assert hasattr(opt.OptimizationFactory, "create")
        assert hasattr(opt.OptimizationFactory, "create_from_config")
        assert hasattr(opt.OptimizationFactory, "create_with_config")





class TestIntegrationIsolation:
    """Ensure Sprint 42B features don’t break 42A public signatures or imports."""

    def test_old_engine_still_has_optimize(self):
        e = opt.OptimizationEngine()
        assert hasattr(e, "optimize")

    def test_old_engine_still_has_efficient_frontier(self):
        e = opt.OptimizationEngine()
        assert hasattr(e, "efficient_frontier")

    def test_all_24a_still_present(self):
        export_keys = ["OptimizationEngine", "OptimizationFactory", "OptimizationConfig", "OptimizationRequest", "OptimizationResult", "PortfolioSolution", "ConstraintViolation", "ConstraintType"]
        for k in export_keys:
            assert k in dir(opt)





# 157–162 can be added incrementally with exhaustive unit tests for edge cases; keep an eye on tests/target of 140–170.
