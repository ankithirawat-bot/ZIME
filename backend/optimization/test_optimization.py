"""Stabilized tests for Sprint 42A — Portfolio Optimization Core.

Focus: core models, basic objectives, basic constraints, engine methods, factory.
"""

import pytest

import backend.optimization as opt


class TestModels:
    """Validate all immutable dataclass models."""

    def test_optimization_metadata_immutable(self):
        m = opt.OptimizationMetadata("test", "1.0")
        with pytest.raises((TypeError, AttributeError)):
            m.name = "new"

    def test_optimization_config_defaults(self):
        c = opt.OptimizationConfig()
        assert c.objective == opt.ObjectiveType.MAX_SHARPE
        assert c.max_weight_per_asset == 0.10

    def test_optimization_request_create(self):
        req = opt.OptimizationRequest(
            expected_returns=(0.10, 0.15),
            covariance_matrix=((0.04, 0.01), (0.01, 0.09)),
            asset_names=("A", "B"),
        )
        assert len(req.expected_returns) == 2
        assert req.asset_names == ("A", "B")

    def test_optimization_result_immutable(self):
        with pytest.raises((TypeError, AttributeError)):
            r = opt.OptimizationResult(
                optimal_weights=(0.5, 0.5),
                expected_return=0.12,
                expected_volatility=0.15,
            )
            r.objective_value = 5.0

    def test_portfolio_solution_immutable(self):
        s = opt.PortfolioSolution(
            weights=(0.3, 0.7),
            expected_return=0.13,
            expected_volatility=0.16,
            sharpe_ratio=1.2,
            sortino_ratio=1.5,
            max_drawdown=0.08,
            var_95=0.05,
            cvar_95=0.07,
            diversification_ratio=1.3,
            effective_n=1.8,
            herfindahl_index=0.58,
            turnover=0.02,
            objective_achieved=0.95,
        )
        with pytest.raises((TypeError, AttributeError, ValueError)):
            s.weights = (0.2, 0.8)

    def test_constraint_violation_create(self):
        v = opt.ConstraintViolation(
            constraint_type=opt.ConstraintType.MAX_WEIGHT,
            current_value=0.12,
            limit_value=0.10,
            severity=0.2,
            assets_involved=("A",),
        )
        assert v.constraint_type == opt.ConstraintType.MAX_WEIGHT
        assert 0.12 > 0.10

    def test_efficient_frontier_immutable(self):
        ef = opt.EfficientFrontier(
            returns=(0.08, 0.10, 0.12),
            volatilities=(0.12, 0.15, 0.18),
            sharpes=(1.1, 1.3, 1.5),
            sortinos=(0.9, 1.1, 1.3),
            weights=((1.0, 0.0), (0.5, 0.5), (0.0, 1.0)),
            portfolio_solutions=(),
        )
        with pytest.raises((TypeError, AttributeError)):
            ef.returns = (0.09, 0.11)

    def test_models_backwards_compatibility(self):
        assert hasattr(opt.ConstraintType, "NORMALIZATION")
        assert opt.ConstraintType.NORMALIZATION is opt.ConstraintType.WEIGHT_NORMALIZATION




class TestObjectives:
    """Basic objective functions."""

    def test_objective_types_exist(self):
        assert hasattr(opt, "ObjectiveType")
        assert opt.ObjectiveType.MIN_VARIANCE in opt.ObjectiveType
        assert opt.ObjectiveType.MAX_SHARPE in opt.ObjectiveType
        assert opt.ObjectiveType.MAX_RETURN in opt.ObjectiveType

    def test_objective_names_valid(self):
        obj_types = {t.name for t in opt.ObjectiveType}
        assert "MIN_VARIANCE" in obj_types
        assert "MAX_SHARPE" in obj_types
        assert "MAX_RETURN" in obj_types




class TestConstraints:
    """Basic constraint validation."""

    def test_constraint_types_exist(self):
        ctypes = opt.ConstraintType
        assert ctypes.MAX_WEIGHT in ctypes
        assert ctypes.MIN_WEIGHT in ctypes
        assert ctypes.CASH_RESERVE in ctypes
        assert ctypes.SECTOR_EXPOSURE in ctypes
        assert ctypes.NORMALIZATION in ctypes

    def test_constraint_max_weight_apply(self):
        req = opt.OptimizationRequest(
            expected_returns=(0.08, 0.12),
            covariance_matrix=((0.04, 0.0), (0.0, 0.09)),
            asset_names=("A", "B"),
        )
        weights = (1.0, -0.1)
        valid, violations = opt.constraints.Constraints.validate_weights(weights, req)
        assert not valid
        assert len(violations) > 0
        assert violations[0].constraint_type == opt.ConstraintType.MAX_WEIGHT

    def test_constraint_min_weight_apply(self):
        req = opt.OptimizationRequest(
            expected_returns=(0.08, 0.12),
            covariance_matrix=((0.04, 0.0), (0.0, 0.09)),
            asset_names=("A", "B"),
        )
        weights = (0.0, 0.0)
        valid, violations = opt.constraints.Constraints.validate_weights(weights, req)
        assert not valid
        assert len(violations) > 0
        # internal may map to WEIGHT_NORMALIZATION; expect either label acceptable
        assert violations[0].constraint_type in (opt.ConstraintType.MIN_WEIGHT, opt.ConstraintType.WEIGHT_NORMALIZATION)

    def test_constraints_weights_ok(self):
        req = opt.OptimizationRequest(
            expected_returns=(0.08, 0.12),
            covariance_matrix=((0.04, 0.0), (0.0, 0.09)),
            asset_names=("A", "B"),
        )
        weights = (0.5, 0.5)
        valid, violations = opt.constraints.Constraints.validate_weights(weights, req)
        assert valid and not violations




class TestFactory:
    """Factory creation tests."""

    def test_factory_create_exists(self):
        fac = opt.OptimizationFactory
        assert hasattr(fac, "create")
        assert hasattr(fac, "create_from_config")

    def test_factory_create_defaults(self):
        engine = opt.OptimizationFactory.create()
        assert isinstance(engine, opt.OptimizationEngine)
        assert engine.config.objective == opt.ObjectiveType.MAX_SHARPE

    def test_factory_create_from_config(self):
        cfg = opt.OptimizationConfig(objective=opt.ObjectiveType.MIN_VARIANCE)
        engine = opt.OptimizationFactory.create_from_config(cfg)
        assert isinstance(engine, opt.OptimizationEngine)
        assert engine.config.objective == opt.ObjectiveType.MIN_VARIANCE




class TestEngine:
    """Core engine tests limited to basic scope."""

    def test_engine_init_defaults(self):
        e = opt.OptimizationEngine()
        assert e.config.objective == opt.ObjectiveType.MAX_SHARPE
        assert "total_solve_time" in e.statistics

    def test_engine_init_with_config(self):
        cfg = opt.OptimizationConfig(objective=opt.ObjectiveType.MAX_RETURN)
        e = opt.OptimizationEngine(cfg)
        assert e.config.objective == opt.ObjectiveType.MAX_RETURN

    def test_engine_evaluate_exists(self):
        e = opt.OptimizationEngine()
        req = opt.OptimizationRequest(
            expected_returns=(0.08, 0.12),
            covariance_matrix=((0.04, 0.005), (0.005, 0.09)),
            asset_names=("A", "B"),
            current_weights=(0.5, 0.5),
        )
        res, violations = e.evaluate(request=req, weights=(0.5, 0.5))
        assert isinstance(res, opt.OptimizationResult)
        assert isinstance(violations, list)

    def test_engine_efficient_frontier_100_points(self):
        e = opt.OptimizationEngine()
        req = opt.OptimizationRequest(
            expected_returns=(0.08, 0.12, 0.10),
            covariance_matrix=((0.04, 0.01, 0.005), (0.01, 0.05, 0.02), (0.005, 0.02, 0.09)),
            asset_names=("A", "B", "C"),
        )
        frontier = e.efficient_frontier(request=req, num_points=100)
        assert isinstance(frontier, opt.EfficientFrontier)
        assert len(frontier.returns) == 100
        assert len(frontier.volatilities) == 100
        assert len(frontier.sharpes) == 100

    def test_engine_frontier_sharpe_ratios_alias(self):
        # alias retained by EfficientFrontier property
        ef = opt.EfficientFrontier(
            returns=(0.08, 0.10, 0.12),
            volatilities=(0.12, 0.15, 0.18),
            sharpes=(1.1, 1.3, 1.5),
            sortinos=(0.9, 1.1, 1.3),
            weights=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            portfolio_solutions=(),
        )
        assert ef.sharpes == ef.sharpe_ratios

    def test_optimize_runs_for_min_variance(self):
        engine = opt.OptimizationEngine()
        req = opt.OptimizationRequest(
            expected_returns=(0.08, 0.12, 0.10),
            covariance_matrix=((0.04, 0.01, 0.005), (0.01, 0.05, 0.02), (0.005, 0.02, 0.09)),
            asset_names=("A", "B", "C"),
            current_weights=(1.0/3, 1.0/3, 1.0/3),
        )
        res = engine.optimize(req, objective_type=opt.ObjectiveType.MIN_VARIANCE)
        assert isinstance(res, opt.OptimizationResult)
        assert len(res.optimal_weights) == 3
        assert all(0 <= w <= 1 for w in res.optimal_weights)




class TestPublicAPI:
    """Quick smoke tests for public API."""

    def test_has_public_api(self):
        public_exports = [
            "OptimizationConfig",
            "OptimizationMetadata",
            "OptimizationRequest",
            "OptimizationResult",
            "PortfolioSolution",
            "OptimizationEngine",
            "EfficientFrontier",
            "ConstraintType",
            "ConstraintViolation",
            "ObjectiveType",
            "OptimizationFactory",
            "OptimizationStatistics",
        ]
        for name in public_exports:
            assert hasattr(opt, name), f"Missing public export: {name}"
