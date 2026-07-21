"""
Ranking engine tests.

Covers normalization, weighting, ranking order, ties, invalid weights,
empty universe, registry, and statistics.
"""

from __future__ import annotations

import pytest

from backend.ranking.exceptions import (
    EmptyUniverseError,
    FactorNotFoundError,
    InvalidWeightsError,
)
from backend.ranking.factory import RankingFactory
from backend.ranking.models import (
    FactorCategory,
    FactorScore,
    NormalizationMethod,
    RankingDefinition,
    RankingDirection,
    RankingEntry,
    RankingFactor,
    RankingMetadata,
    RankingResult,
    RankingStatistics,
)
from backend.ranking.normalization import (
    normalize,
    normalize_factor_scores,
    normalize_min_max,
    normalize_percentile,
    normalize_z_score,
)
from backend.ranking.registry import FactorRegistry, build_default_factor_registry
from backend.ranking.weights import (
    apply_weights,
    equalize_weights,
    normalize_weights,
    validate_weights,
)

# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------


def _make_data(
    roe: float = 20.0,
    roce: float = 25.0,
    sales_growth: float = 15.0,
    debt_equity: float = 0.5,
) -> dict:
    """Create test data dictionary."""
    return {
        "fundamentals": {
            "roe": roe,
            "roce": roce,
            "sales_growth": sales_growth,
            "debt_equity": debt_equity,
        },
        "technicals": {
            "rs_score": roe * 2,
            "trend_score": roce * 1.5,
        },
        "quality": {
            "data_confidence": 90.0,
            "liquidity_score": 80.0,
        },
    }


def _simple_definition(
    name: str = "Test Ranking",
    factors: tuple[RankingFactor, ...] | None = None,
) -> RankingDefinition:
    """Create a simple ranking definition for testing."""
    if factors is None:
        factors = (
            RankingFactor(
                name="roe",
                weight=0.5,
                category=FactorCategory.FUNDAMENTAL,
                direction=RankingDirection.HIGHER_IS_BETTER,
            ),
            RankingFactor(
                name="roce",
                weight=0.5,
                category=FactorCategory.FUNDAMENTAL,
                direction=RankingDirection.HIGHER_IS_BETTER,
            ),
        )
    return RankingDefinition(
        metadata=RankingMetadata(name=name),
        factors=factors,
    )


# ---------------------------------------------------------------------------
# Normalization tests
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_min_max(self):
        values = (10.0, 20.0, 30.0, 40.0, 50.0)
        result = normalize_min_max(values)
        assert result[0] == pytest.approx(0.0)
        assert result[-1] == pytest.approx(1.0)
        assert result[2] == pytest.approx(0.5)

    def test_min_max_single_value(self):
        result = normalize_min_max((10.0,))
        assert result[0] == pytest.approx(0.5)

    def test_min_max_equal_values(self):
        result = normalize_min_max((10.0, 10.0, 10.0))
        assert all(v == pytest.approx(0.5) for v in result)

    def test_min_max_empty(self):
        result = normalize_min_max(())
        assert result == ()

    def test_z_score(self):
        values = (10.0, 20.0, 30.0, 40.0, 50.0)
        result = normalize_z_score(values)
        assert len(result) == 5
        assert sum(result) == pytest.approx(0.0, abs=1e-10)

    def test_z_score_single_value(self):
        result = normalize_z_score((10.0,))
        assert result[0] == pytest.approx(0.0)

    def test_z_score_equal_values(self):
        result = normalize_z_score((10.0, 10.0, 10.0))
        assert all(v == pytest.approx(0.0) for v in result)

    def test_z_score_empty(self):
        result = normalize_z_score(())
        assert result == ()

    def test_percentile(self):
        values = (10.0, 20.0, 30.0, 40.0, 50.0)
        result = normalize_percentile(values)
        assert result[0] == pytest.approx(0.0)
        assert result[-1] == pytest.approx(1.0)

    def test_percentile_single_value(self):
        result = normalize_percentile((10.0,))
        assert result[0] == pytest.approx(1.0)

    def test_percentile_empty(self):
        result = normalize_percentile(())
        assert result == ()

    def test_normalize_min_max(self):
        values = (10.0, 20.0, 30.0)
        result = normalize(values, NormalizationMethod.MIN_MAX)
        assert result[0] == pytest.approx(0.0)
        assert result[-1] == pytest.approx(1.0)

    def test_normalize_z_score(self):
        values = (10.0, 20.0, 30.0)
        result = normalize(values, NormalizationMethod.Z_SCORE)
        assert len(result) == 3

    def test_normalize_percentile(self):
        values = (10.0, 20.0, 30.0)
        result = normalize(values, NormalizationMethod.PERCENTILE)
        assert result[0] == pytest.approx(0.0)
        assert result[-1] == pytest.approx(1.0)

    def test_normalize_lower_is_better(self):
        values = (10.0, 20.0, 30.0)
        result = normalize(
            values, NormalizationMethod.MIN_MAX, RankingDirection.LOWER_IS_BETTER
        )
        assert result[0] == pytest.approx(1.0)
        assert result[-1] == pytest.approx(0.0)

    def test_normalize_factor_scores(self):
        values = (10.0, 20.0, 30.0)
        result = normalize_factor_scores(
            values, NormalizationMethod.MIN_MAX, RankingDirection.HIGHER_IS_BETTER
        )
        assert result[0] == pytest.approx(0.0)
        assert result[-1] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Weights tests
# ---------------------------------------------------------------------------


class TestWeights:
    def test_validate_weights_valid(self):
        factors = (
            RankingFactor(name="a", weight=0.5),
            RankingFactor(name="b", weight=0.5),
        )
        assert validate_weights(factors) is True

    def test_validate_weights_invalid_total(self):
        factors = (
            RankingFactor(name="a", weight=0.5),
            RankingFactor(name="b", weight=0.6),
        )
        with pytest.raises(InvalidWeightsError, match="must total 1.0"):
            validate_weights(factors)

    def test_validate_weights_negative(self):
        factors = (
            RankingFactor(name="a", weight=-0.5),
            RankingFactor(name="b", weight=1.5),
        )
        with pytest.raises(InvalidWeightsError, match="non-negative"):
            validate_weights(factors)

    def test_validate_weights_empty(self):
        with pytest.raises(InvalidWeightsError, match="No factors"):
            validate_weights(())

    def test_normalize_weights(self):
        factors = (
            RankingFactor(name="a", weight=2.0),
            RankingFactor(name="b", weight=3.0),
        )
        result = normalize_weights(factors)
        assert result[0].weight == pytest.approx(0.4)
        assert result[1].weight == pytest.approx(0.6)

    def test_normalize_weights_zero_total(self):
        factors = (
            RankingFactor(name="a", weight=0.0),
            RankingFactor(name="b", weight=0.0),
        )
        result = normalize_weights(factors)
        assert result[0].weight == pytest.approx(0.5)
        assert result[1].weight == pytest.approx(0.5)

    def test_equalize_weights(self):
        factors = (
            RankingFactor(name="a", weight=1.0),
            RankingFactor(name="b", weight=2.0),
            RankingFactor(name="c", weight=3.0),
        )
        result = equalize_weights(factors)
        for f in result:
            assert f.weight == pytest.approx(1.0 / 3)

    def test_apply_weights(self):
        scores = {"a": 0.8, "b": 0.6}
        weights = {"a": 0.5, "b": 0.5}
        result = apply_weights(scores, weights)
        assert result == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# Factor Registry tests
# ---------------------------------------------------------------------------


class TestFactorRegistry:
    def test_default_factors(self):
        registry = build_default_factor_registry()
        assert registry.is_registered("roe")
        assert registry.is_registered("roce")
        assert registry.is_registered("debt_equity")
        assert registry.is_registered("relative_strength")

    def test_custom_factor(self):
        registry = FactorRegistry(load_defaults=False)

        def custom_func(data: dict) -> float:
            return data.get("custom", 0.0)

        registry.register("custom_factor", custom_func, FactorCategory.CUSTOM)
        assert registry.is_registered("custom_factor")
        assert registry.get("custom_factor")({"custom": 42.0}) == 42.0

    def test_get_unregistered_factor(self):
        registry = FactorRegistry(load_defaults=False)
        with pytest.raises(FactorNotFoundError):
            registry.get("nonexistent")

    def test_factor_by_category(self):
        registry = build_default_factor_registry()
        fundamental = registry.factors_by_category(FactorCategory.FUNDAMENTAL)
        assert "roe" in fundamental
        assert "roce" in fundamental

    def test_get_direction(self):
        registry = build_default_factor_registry()
        direction = registry.get_direction("debt_equity")
        assert direction == RankingDirection.LOWER_IS_BETTER

    def test_registered_names(self):
        registry = build_default_factor_registry()
        names = registry.registered_names()
        assert "roe" in names
        assert len(names) > 10


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestModels:
    def test_ranking_metadata(self):
        meta = RankingMetadata(name="Test", author="Author", tags=("a", "b"))
        assert meta.name == "Test"
        assert meta.tags == ("a", "b")

    def test_ranking_factor(self):
        factor = RankingFactor(
            name="roe",
            weight=0.5,
            category=FactorCategory.FUNDAMENTAL,
        )
        assert factor.name == "roe"
        assert factor.weight == 0.5

    def test_factor_score(self):
        score = FactorScore(
            factor_name="roe",
            symbol="RELIANCE",
            raw_value=20.0,
            normalized=0.8,
            weight=0.5,
            weighted=0.4,
        )
        assert score.raw_value == 20.0
        assert score.weighted == 0.4

    def test_ranking_entry(self):
        entry = RankingEntry(
            symbol="RELIANCE",
            rank=1,
            total_score=0.85,
        )
        assert entry.rank == 1
        assert entry.total_score == 0.85

    def test_ranking_result(self):
        result = RankingResult(
            ranking_name="Test",
            entries=(),
        )
        assert result.ranking_name == "Test"
        assert result.entries == ()

    def test_ranking_statistics(self):
        stats = RankingStatistics(
            total_symbols=100,
            total_factors=5,
            mean_score=0.6,
        )
        assert stats.total_symbols == 100
        assert stats.mean_score == 0.6


# ---------------------------------------------------------------------------
# Ranking Engine tests
# ---------------------------------------------------------------------------


class TestRankingEngine:
    def test_rank_basic(self):
        engine = RankingFactory.create()
        definition = _simple_definition()
        symbols_data = {
            "RELIANCE": _make_data(roe=25, roce=30),
            "TCS": _make_data(roe=20, roce=25),
            "INFY": _make_data(roe=15, roce=20),
        }

        result = engine.rank(definition, symbols_data)

        assert result.ranking_name == "Test Ranking"
        assert len(result.entries) == 3
        assert result.entries[0].symbol == "RELIANCE"
        assert result.entries[0].rank == 1
        assert result.entries[1].rank == 2
        assert result.entries[2].rank == 3

    def test_rank_order(self):
        engine = RankingFactory.create()
        definition = _simple_definition()
        symbols_data = {
            "A": _make_data(roe=10, roce=10),
            "B": _make_data(roe=30, roce=30),
            "C": _make_data(roe=20, roce=20),
        }

        result = engine.rank(definition, symbols_data)

        assert result.entries[0].symbol == "B"
        assert result.entries[1].symbol == "C"
        assert result.entries[2].symbol == "A"

    def test_rank_ties(self):
        engine = RankingFactory.create()
        definition = _simple_definition()
        symbols_data = {
            "A": _make_data(roe=20, roce=25),
            "B": _make_data(roe=20, roce=25),
        }

        result = engine.rank(definition, symbols_data)

        assert len(result.entries) == 2
        assert result.entries[0].total_score == result.entries[1].total_score

    def test_rank_empty_universe(self):
        engine = RankingFactory.create()
        definition = _simple_definition()

        with pytest.raises(EmptyUniverseError):
            engine.rank(definition, {})

    def test_rank_single_symbol(self):
        engine = RankingFactory.create()
        definition = _simple_definition()
        symbols_data = {"RELIANCE": _make_data(roe=25, roce=30)}

        result = engine.rank(definition, symbols_data)

        assert len(result.entries) == 1
        assert result.entries[0].symbol == "RELIANCE"
        assert result.entries[0].rank == 1

    def test_rank_with_z_score(self):
        factors = (
            RankingFactor(
                name="roe",
                weight=0.5,
                normalization=NormalizationMethod.Z_SCORE,
            ),
            RankingFactor(
                name="roce",
                weight=0.5,
                normalization=NormalizationMethod.Z_SCORE,
            ),
        )
        definition = _simple_definition(factors=factors)
        engine = RankingFactory.create()
        symbols_data = {
            "A": _make_data(roe=10, roce=15),
            "B": _make_data(roe=20, roce=25),
            "C": _make_data(roe=30, roce=35),
        }

        result = engine.rank(definition, symbols_data)

        assert len(result.entries) == 3
        assert result.entries[0].symbol == "C"

    def test_rank_with_percentile(self):
        factors = (
            RankingFactor(
                name="roe",
                weight=1.0,
                normalization=NormalizationMethod.PERCENTILE,
            ),
        )
        definition = _simple_definition(factors=factors)
        engine = RankingFactory.create()
        symbols_data = {
            "A": _make_data(roe=10),
            "B": _make_data(roe=20),
            "C": _make_data(roe=30),
        }

        result = engine.rank(definition, symbols_data)

        assert result.entries[0].symbol == "C"
        assert result.entries[2].symbol == "A"

    def test_rank_lower_is_better(self):
        factors = (
            RankingFactor(
                name="debt_equity",
                weight=1.0,
                direction=RankingDirection.LOWER_IS_BETTER,
            ),
        )
        definition = _simple_definition(factors=factors)
        engine = RankingFactory.create()
        symbols_data = {
            "A": _make_data(debt_equity=2.0),
            "B": _make_data(debt_equity=0.5),
            "C": _make_data(debt_equity=1.0),
        }

        result = engine.rank(definition, symbols_data)

        assert result.entries[0].symbol == "B"
        assert result.entries[2].symbol == "A"

    def test_rank_statistics(self):
        engine = RankingFactory.create()
        definition = _simple_definition()
        symbols_data = {
            "A": _make_data(roe=10, roce=15),
            "B": _make_data(roe=20, roce=25),
            "C": _make_data(roe=30, roce=35),
        }

        result = engine.rank(definition, symbols_data)

        assert result.statistics.total_symbols == 3
        assert result.statistics.total_factors == 2
        assert result.statistics.elapsed_seconds >= 0
        assert result.statistics.mean_score > 0

    def test_rank_factor_scores(self):
        engine = RankingFactory.create()
        definition = _simple_definition()
        symbols_data = {
            "RELIANCE": _make_data(roe=25, roce=30),
        }

        result = engine.rank(definition, symbols_data)

        entry = result.entries[0]
        assert len(entry.factor_scores) == 2
        assert entry.factor_scores[0].factor_name == "roe"
        assert entry.factor_scores[0].symbol == "RELIANCE"
        assert entry.factor_scores[0].raw_value == 25.0


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


class TestRankingFactory:
    def test_create_default(self):
        engine = RankingFactory.create()
        assert engine is not None
        assert engine.factor_registry.is_registered("roe")

    def test_create_custom_factors_only(self):
        engine = RankingFactory.create_with_custom_factors()
        assert not engine.factor_registry.is_registered("roe")

    def test_create_from_registry(self):
        registry = FactorRegistry(load_defaults=False)
        engine = RankingFactory.create_from_registry(registry)
        assert not engine.factor_registry.is_registered("roe")


# ---------------------------------------------------------------------------
# Exception tests
# ---------------------------------------------------------------------------


class TestExceptions:
    def test_ranking_error(self):
        from backend.ranking.exceptions import RankingError

        with pytest.raises(RankingError):
            raise RankingError("test")

    def test_factor_not_found(self):
        with pytest.raises(FactorNotFoundError) as excinfo:
            raise FactorNotFoundError("my_factor")
        assert excinfo.value.name == "my_factor"
        assert "my_factor" in str(excinfo.value)

    def test_empty_universe(self):
        with pytest.raises(EmptyUniverseError):
            raise EmptyUniverseError()

    def test_invalid_weights(self):
        with pytest.raises(InvalidWeightsError, match="bad"):
            raise InvalidWeightsError("bad weights")


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_complete_ranking_flow(self):
        """Test a complete ranking flow with multiple factors."""
        definition = RankingDefinition(
            metadata=RankingMetadata(name="Quality Ranking"),
            factors=(
                RankingFactor(
                    name="roe",
                    weight=0.25,
                    category=FactorCategory.FUNDAMENTAL,
                    direction=RankingDirection.HIGHER_IS_BETTER,
                ),
                RankingFactor(
                    name="roce",
                    weight=0.25,
                    category=FactorCategory.FUNDAMENTAL,
                    direction=RankingDirection.HIGHER_IS_BETTER,
                ),
                RankingFactor(
                    name="sales_growth",
                    weight=0.25,
                    category=FactorCategory.FUNDAMENTAL,
                    direction=RankingDirection.HIGHER_IS_BETTER,
                ),
                RankingFactor(
                    name="debt_equity",
                    weight=0.25,
                    category=FactorCategory.FUNDAMENTAL,
                    direction=RankingDirection.LOWER_IS_BETTER,
                ),
            ),
        )

        engine = RankingFactory.create()
        symbols_data = {
            "RELIANCE": _make_data(roe=25, roce=30, sales_growth=20, debt_equity=0.3),
            "TCS": _make_data(roe=35, roce=40, sales_growth=15, debt_equity=0.1),
            "INFY": _make_data(roe=20, roce=25, sales_growth=25, debt_equity=0.5),
            "HDFCBANK": _make_data(roe=18, roce=22, sales_growth=12, debt_equity=0.2),
        }

        result = engine.rank(definition, symbols_data)

        assert result.ranking_name == "Quality Ranking"
        assert len(result.entries) == 4
        assert result.statistics.total_symbols == 4
        assert result.statistics.total_factors == 4

        for entry in result.entries:
            assert entry.rank > 0
            assert entry.total_score >= 0
            assert len(entry.factor_scores) == 4

    def test_all_builtin_factors_registered(self):
        """Verify all built-in factors are registered."""
        registry = build_default_factor_registry()

        expected_factors = [
            "roce", "roe", "sales_growth", "profit_growth", "eps_growth",
            "debt_equity", "operating_margin",
            "relative_strength", "trend_score", "momentum_score",
            "volume_score", "volatility_score",
            "data_quality_confidence", "liquidity_score",
        ]

        for name in expected_factors:
            assert registry.is_registered(name), f"Factor '{name}' not registered"

    def test_weight_validation_in_definition(self):
        """Test that weights are validated."""
        from backend.ranking.weights import validate_weights

        definition = _simple_definition()
        assert validate_weights(definition.factors) is True

        invalid_factors = (
            RankingFactor(name="a", weight=0.3),
            RankingFactor(name="b", weight=0.3),
        )
        with pytest.raises(InvalidWeightsError):
            validate_weights(invalid_factors)
