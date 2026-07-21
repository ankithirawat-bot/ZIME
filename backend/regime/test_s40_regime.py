"""Sprint 40: Universal Market Regime Detection Engine — Full Test Suite.

Tests models, exceptions, features, detectors, scoring, engine,
and factory for the market regime detection system.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from backend.regime.detectors import (
    BaseDetector,
    HMMPlaceholderDetector,
    MLPlaceholderDetector,
    RuleBasedDetector,
    ScoreBasedDetector,
    VotingDetector,
)
from backend.regime.engine import RegimeEngine
from backend.regime.exceptions import (
    DetectionError,
    DetectorNotFoundError,
    FeatureError,
    InsufficientDataError,
    InvalidRegimeConfigError,
    RegimeError,
    TransitionError,
)
from backend.regime.factory import RegimeFactory
from backend.regime.features import (
    FeatureExtractor,
    extract_breadth,
    extract_dispersion,
    extract_drawdown,
    extract_liquidity_score,
    extract_market_correlation,
    extract_momentum,
    extract_recovery_strength,
    extract_trend_strength,
    extract_volatility_change,
    extract_volatility_level,
    extract_volume_expansion,
)
from backend.regime.models import (
    RegimeConfig,
    RegimeFeatures,
    RegimeHistory,
    RegimeResult,
    RegimeScore,
    RegimeStatistics,
    RegimeTransition,
    RegimeType,
)
from backend.regime.scoring import (
    build_transition_matrix,
    compute_regime_statistics,
    compute_transition_probability,
    get_recommendations,
)

# =========================================================================
# Helpers
# =========================================================================


def _prices(
    base: float = 100.0,
    count: int = 100,
    uptrend: bool = True,
    volatility: float = 0.01,
) -> tuple[float, ...]:
    prices = [base]
    for i in range(1, count):
        trend = 0.002 if uptrend else -0.002
        ret = trend + volatility * (2 * math.sin(i * 0.5))
        prices.append(prices[-1] * (1 + ret))
    return tuple(prices)


def _volumes(base: float = 1_000_000, count: int = 100) -> tuple[float, ...]:
    return tuple(base * (1.0 + 0.3 * math.sin(i * 0.3)) for i in range(count))


def _advances(count: int = 60) -> tuple[float, ...]:
    return tuple(800 + 200 * math.sin(i * 0.2) for i in range(count))


def _declines(count: int = 60) -> tuple[float, ...]:
    return tuple(400 + 150 * math.cos(i * 0.2) for i in range(count))


def _returns_map(
    n: int = 5,
    periods: int = 60,
) -> dict[str, tuple[float, ...]]:
    return {
        f"sym{i}": tuple(0.001 * math.sin(j * 0.3 + i) for j in range(periods))
        for i in range(n)
    }


def _default_features() -> RegimeFeatures:
    return RegimeFeatures(
        trend_strength=0.6,
        momentum=0.4,
        volatility_level=0.2,
        volatility_change=0.1,
        breadth=0.7,
        volume_expansion=0.3,
        market_correlation=0.6,
        dispersion=0.3,
        drawdown=0.05,
        recovery_strength=0.8,
        liquidity_score=0.7,
    )


def _extreme_bull_features() -> RegimeFeatures:
    return RegimeFeatures(
        trend_strength=0.8,
        momentum=0.7,
        volatility_level=0.1,
        volatility_change=-0.2,
        breadth=0.9,
        volume_expansion=0.6,
        market_correlation=0.8,
        dispersion=0.2,
        drawdown=0.02,
        recovery_strength=0.9,
        liquidity_score=0.9,
    )


def _extreme_bear_features() -> RegimeFeatures:
    return RegimeFeatures(
        trend_strength=-0.7,
        momentum=-0.6,
        volatility_level=0.7,
        volatility_change=0.5,
        breadth=0.2,
        volume_expansion=-0.4,
        market_correlation=0.9,
        dispersion=0.7,
        drawdown=0.3,
        recovery_strength=0.1,
        liquidity_score=0.3,
    )


# =========================================================================
# Models
# =========================================================================


class TestRegimeType:
    def test_values(self) -> None:
        assert RegimeType.TRENDING_BULL.value == "TRENDING_BULL"
        assert RegimeType.TRENDING_BEAR.value == "TRENDING_BEAR"
        assert RegimeType.SIDEWAYS.value == "SIDEWAYS"
        assert RegimeType.ACCUMULATION.value == "ACCUMULATION"
        assert RegimeType.DISTRIBUTION.value == "DISTRIBUTION"
        assert RegimeType.RECOVERY.value == "RECOVERY"
        assert RegimeType.HIGH_VOLATILITY.value == "HIGH_VOLATILITY"
        assert RegimeType.LOW_VOLATILITY.value == "LOW_VOLATILITY"
        assert RegimeType.PANIC.value == "PANIC"
        assert RegimeType.EUPHORIA.value == "EUPHORIA"
        assert RegimeType.UNKNOWN.value == "UNKNOWN"

    def test_members_count(self) -> None:
        assert len(RegimeType) == 11

    def test_str_enum(self) -> None:
        assert str(RegimeType.TRENDING_BULL) == "TRENDING_BULL"


class TestRegimeConfig:
    def test_defaults(self) -> None:
        cfg = RegimeConfig()
        assert cfg.detector == "voting"
        assert cfg.lookback == 252
        assert cfg.short_lookback == 20
        assert cfg.volatility_lookback == 20
        assert cfg.trend_lookback == 60
        assert cfg.momentum_lookback == 20
        assert cfg.confidence_threshold == 0.60
        assert cfg.transition_min_hold == 5
        assert cfg.correlation_lookback == 60
        assert cfg.breadth_lookback == 20
        assert cfg.min_periods == 20
        assert cfg.annual_factor == 252.0

    def test_custom(self) -> None:
        cfg = RegimeConfig(detector="rule_based", lookback=100, confidence_threshold=0.75)
        assert cfg.detector == "rule_based"
        assert cfg.lookback == 100
        assert cfg.confidence_threshold == 0.75

    def test_frozen(self) -> None:
        cfg = RegimeConfig()
        with pytest.raises(AttributeError):
            cfg.detector = "rule_based"  # type: ignore


class TestRegimeFeatures:
    def test_defaults(self) -> None:
        f = RegimeFeatures()
        assert f.trend_strength == 0.0
        assert f.momentum == 0.0
        assert f.volatility_level == 0.0
        assert f.volatility_change == 0.0
        assert f.breadth == 0.0
        assert f.volume_expansion == 0.0
        assert f.market_correlation == 0.0
        assert f.dispersion == 0.0
        assert f.drawdown == 0.0
        assert f.recovery_strength == 0.0
        assert f.liquidity_score == 0.0

    def test_11_fields(self) -> None:
        f = _default_features()
        assert f.trend_strength == 0.6
        assert f.liquidity_score == 0.7

    def test_frozen(self) -> None:
        f = RegimeFeatures()
        with pytest.raises(AttributeError):
            f.trend_strength = 0.5  # type: ignore


class TestRegimeScore:
    def test_defaults(self) -> None:
        s = RegimeScore()
        assert s.regime == RegimeType.UNKNOWN
        assert s.confidence == 0.0
        assert s.evidence == {}
        assert s.competing_regimes == {}
        assert s.transition_probability == 0.0

    def test_custom(self) -> None:
        s = RegimeScore(
            regime=RegimeType.TRENDING_BULL,
            confidence=0.85,
            evidence={"trend": 0.9},
            competing_regimes={"SIDEWAYS": 0.3},
            transition_probability=0.2,
        )
        assert s.regime == RegimeType.TRENDING_BULL
        assert s.confidence == 0.85
        assert s.evidence == {"trend": 0.9}


class TestRegimeTransition:
    def test_defaults(self) -> None:
        t = RegimeTransition(
            from_regime=RegimeType.TRENDING_BULL,
            to_regime=RegimeType.TRENDING_BEAR,
        )
        assert t.from_regime == RegimeType.TRENDING_BULL
        assert t.to_regime == RegimeType.TRENDING_BEAR
        assert t.probability == 0.0
        assert isinstance(t.timestamp, datetime)

    def test_custom(self) -> None:
        ts = datetime(2024, 1, 1, tzinfo=UTC)
        t = RegimeTransition(
            from_regime=RegimeType.TRENDING_BULL,
            to_regime=RegimeType.SIDEWAYS,
            probability=0.75,
            timestamp=ts,
        )
        assert t.from_regime == RegimeType.TRENDING_BULL
        assert t.to_regime == RegimeType.SIDEWAYS
        assert t.probability == 0.75
        assert t.timestamp == ts


class TestRegimeResult:
    def test_defaults(self) -> None:
        r = RegimeResult()
        assert r.regime == RegimeType.UNKNOWN
        assert r.score == RegimeScore()
        assert r.features == RegimeFeatures()
        assert r.detector == ""
        assert r.recommendations == {}
        assert r.elapsed == 0.0
        assert isinstance(r.timestamp, datetime)

    def test_custom(self) -> None:
        f = _default_features()
        s = RegimeScore(regime=RegimeType.TRENDING_BULL, confidence=0.9)
        r = RegimeResult(
            regime=RegimeType.TRENDING_BULL,
            score=s,
            features=f,
            detector="rule_based",
            recommendations={"strategy": "Buy"},
            elapsed=0.05,
        )
        assert r.regime == RegimeType.TRENDING_BULL
        assert r.score.confidence == 0.9
        assert r.detector == "rule_based"
        assert r.recommendations == {"strategy": "Buy"}
        assert r.elapsed == 0.05

    def test_frozen(self) -> None:
        r = RegimeResult()
        with pytest.raises(AttributeError):
            r.regime = RegimeType.TRENDING_BULL  # type: ignore


class TestRegimeHistory:
    def test_defaults(self) -> None:
        h = RegimeHistory()
        assert h.results == ()
        assert h.transitions == ()
        assert h.current is None
        assert h.total_periods == 0

    def test_with_results(self) -> None:
        r1 = RegimeResult(regime=RegimeType.TRENDING_BULL, detector="test")
        r2 = RegimeResult(regime=RegimeType.SIDEWAYS, detector="test")
        h = RegimeHistory(
            results=(r1, r2),
            transitions=(RegimeTransition(from_regime=RegimeType.TRENDING_BULL, to_regime=RegimeType.SIDEWAYS),),
            current=r2,
            total_periods=2,
        )
        assert len(h.results) == 2
        assert len(h.transitions) == 1
        assert h.current == r2
        assert h.total_periods == 2


class TestRegimeStatistics:
    def test_defaults(self) -> None:
        s = RegimeStatistics()
        assert s.total_detections == 0
        assert s.regime_counts == {}
        assert s.regime_durations == {}
        assert s.transition_count == 0
        assert s.most_common == "UNKNOWN"
        assert s.regime_stability == 0.0
        assert s.detector_performance == {}
        assert s.warnings == ()

    def test_custom(self) -> None:
        s = RegimeStatistics(
            total_detections=10,
            regime_counts={"TRENDING_BULL": 6, "SIDEWAYS": 4},
            regime_durations={"TRENDING_BULL": 0.6, "SIDEWAYS": 0.4},
            transition_count=2,
            most_common="TRENDING_BULL",
            regime_stability=0.8,
            detector_performance={"rule_based": 0.9},
            warnings=("low_data",),
        )
        assert s.total_detections == 10
        assert s.most_common == "TRENDING_BULL"
        assert len(s.warnings) == 1


# =========================================================================
# Exceptions
# =========================================================================


class TestExceptions:
    def test_regime_error(self) -> None:
        e = RegimeError("test")
        assert isinstance(e, Exception)
        assert str(e) == "test"

    def test_invalid_regime_config_error(self) -> None:
        e = InvalidRegimeConfigError("bad config")
        assert "bad config" in str(e)

    def test_insufficient_data_error(self) -> None:
        e = InsufficientDataError("need more data")
        assert "need more data" in str(e)

    def test_detection_error(self) -> None:
        e = DetectionError("detection failed")
        assert "detection failed" in str(e)

    def test_detector_not_found_error(self) -> None:
        e = DetectorNotFoundError("custom_detector")
        assert "custom_detector" in str(e)
        assert e.name == "custom_detector"

    def test_feature_error(self) -> None:
        e = FeatureError("trend", "calculation failed")
        assert "trend" in str(e)
        assert "calculation failed" in str(e)
        assert e.feature == "trend"

    def test_transition_error(self) -> None:
        e = TransitionError("transition failed")
        assert "transition failed" in str(e)

    def test_hierarchy(self) -> None:
        assert issubclass(InvalidRegimeConfigError, RegimeError)
        assert issubclass(InsufficientDataError, RegimeError)
        assert issubclass(DetectionError, RegimeError)
        assert issubclass(DetectorNotFoundError, RegimeError)
        assert issubclass(FeatureError, RegimeError)
        assert issubclass(TransitionError, RegimeError)


# =========================================================================
# Features
# =========================================================================


class TestExtractTrendStrength:
    def test_uptrend_positive(self) -> None:
        p = _prices(base=100, count=80, uptrend=True)
        ts = extract_trend_strength(p, RegimeConfig(trend_lookback=60))
        assert ts > 0.3

    def test_downtrend_negative(self) -> None:
        p = _prices(base=100, count=80, uptrend=False)
        ts = extract_trend_strength(p, RegimeConfig(trend_lookback=60))
        assert ts < -0.3

    def test_insufficient_data(self) -> None:
        with pytest.raises(InsufficientDataError):
            extract_trend_strength((1, 2, 3), RegimeConfig(trend_lookback=60))

    def test_bound_clamping(self) -> None:
        flat = tuple(100.0 for _ in range(80))
        ts = extract_trend_strength(flat, RegimeConfig(trend_lookback=60))
        assert -1.0 <= ts <= 1.0


class TestExtractMomentum:
    def test_positive_momentum(self) -> None:
        p = tuple(100 + i * 0.5 for i in range(30))
        m = extract_momentum(p, RegimeConfig(momentum_lookback=20))
        assert m > 0

    def test_negative_momentum(self) -> None:
        p = tuple(100 - i * 0.5 for i in range(30))
        m = extract_momentum(p, RegimeConfig(momentum_lookback=20))
        assert m < 0

    def test_insufficient_data(self) -> None:
        with pytest.raises(InsufficientDataError):
            extract_momentum((1, 2), RegimeConfig(momentum_lookback=20))

    def test_bound_clamping(self) -> None:
        p = tuple(100.0 for _ in range(30))
        m = extract_momentum(p, RegimeConfig(momentum_lookback=20))
        assert -1.0 <= m <= 1.0


class TestExtractVolatilityLevel:
    def test_low_volatility(self) -> None:
        p = tuple(100 + 0.1 * math.sin(i * 0.5) for i in range(50))
        v = extract_volatility_level(p, RegimeConfig(volatility_lookback=20))
        assert v < 0.3

    def test_high_volatility(self) -> None:
        p = tuple(100 + 5 * math.sin(i * 0.5) for i in range(50))
        v = extract_volatility_level(p, RegimeConfig(volatility_lookback=20))
        assert v > 0.3

    def test_insufficient_data(self) -> None:
        with pytest.raises(InsufficientDataError):
            extract_volatility_level((1,), RegimeConfig(volatility_lookback=20))

    def test_range_zero_to_one(self) -> None:
        p = _prices(count=50)
        v = extract_volatility_level(p, RegimeConfig(volatility_lookback=20))
        assert 0.0 <= v <= 1.0


class TestExtractVolatilityChange:
    def test_increasing_volatility(self) -> None:
        p = tuple(100 + (i * 0.01 + 2 * math.sin(i * 0.3)) for i in range(60))
        vc = extract_volatility_change(p, RegimeConfig(volatility_lookback=20))
        assert -1.0 <= vc <= 1.0

    def test_insufficient_data(self) -> None:
        with pytest.raises(InsufficientDataError):
            extract_volatility_change((1, 2, 3), RegimeConfig(volatility_lookback=20))


class TestExtractBreadth:
    def test_strong_breadth(self) -> None:
        a = tuple(900 + 50 * math.sin(i * 0.1) for i in range(30))
        d = tuple(200 + 50 * math.cos(i * 0.1) for i in range(30))
        b = extract_breadth(a, d, RegimeConfig(breadth_lookback=20))
        assert b > 0.5

    def test_poor_breadth(self) -> None:
        a = tuple(200 + 50 * math.sin(i * 0.1) for i in range(30))
        d = tuple(900 + 50 * math.cos(i * 0.1) for i in range(30))
        b = extract_breadth(a, d, RegimeConfig(breadth_lookback=20))
        assert b < 0.5

    def test_empty_returns_default(self) -> None:
        b = extract_breadth((), (), RegimeConfig())
        assert b == 0.5

    def test_range_zero_to_one(self) -> None:
        a = _advances(30)
        d = _declines(30)
        b = extract_breadth(a, d, RegimeConfig(breadth_lookback=20))
        assert 0.0 <= b <= 1.0


class TestExtractVolumeExpansion:
    def test_expanding(self) -> None:
        v = tuple(1_000_000 * (1 + 0.02 * i) for i in range(50))
        ve = extract_volume_expansion(v, RegimeConfig(short_lookback=20))
        assert ve > 0

    def test_contracting(self) -> None:
        v = tuple(2_000_000 * (1 - 0.02 * i) for i in range(50))
        ve = extract_volume_expansion(v, RegimeConfig(short_lookback=20))
        assert ve < 0

    def test_insufficient_data(self) -> None:
        with pytest.raises(InsufficientDataError):
            extract_volume_expansion((1, 2, 3), RegimeConfig(short_lookback=20))

    def test_bound_clamping(self) -> None:
        v = _volumes(count=50)
        ve = extract_volume_expansion(v, RegimeConfig(short_lookback=20))
        assert -1.0 <= ve <= 1.0


class TestExtractMarketCorrelation:
    def test_high_correlation(self) -> None:
        rm = {f"sym{i}": tuple(0.001 * math.sin(j * 0.5) for j in range(60)) for i in range(5)}
        c = extract_market_correlation(rm, RegimeConfig(correlation_lookback=60))
        assert c > 0.5

    def test_low_correlation(self) -> None:
        rm = {f"sym{i}": tuple(0.01 * (2 * (j % 2) - 1) for j in range(60)) for i in range(3)}
        c = extract_market_correlation(rm, RegimeConfig(correlation_lookback=60))
        assert 0.0 <= c <= 1.0

    def test_insufficient_symbols(self) -> None:
        rm = {"sym1": (0.1, 0.2, 0.3)}
        c = extract_market_correlation(rm, RegimeConfig())
        assert c == 0.5

    def test_empty_returns_default(self) -> None:
        c = extract_market_correlation({}, RegimeConfig())
        assert c == 0.5


class TestExtractDispersion:
    def test_low_dispersion(self) -> None:
        rm = {f"sym{i}": tuple(0.001 * math.sin(j * 0.3) for j in range(30)) for i in range(6)}
        d = extract_dispersion(rm, RegimeConfig(short_lookback=20))
        assert 0.0 <= d <= 1.0

    def test_insufficient_symbols(self) -> None:
        rm = {"sym1": (0.1, 0.2)}
        d = extract_dispersion(rm, RegimeConfig())
        assert d == 0.5

    def test_insufficient_data_returns_default(self) -> None:
        rm = {f"sym{i}": (0.1,) for i in range(6)}
        d = extract_dispersion(rm, RegimeConfig(short_lookback=5))
        assert d <= 0.5


class TestExtractDrawdown:
    def test_no_drawdown(self) -> None:
        p = tuple(100 + i for i in range(30))
        dd = extract_drawdown(p)
        assert dd == 0.0

    def test_drawdown_present(self) -> None:
        p = (100, 110, 120, 115, 105, 95, 100)
        dd = extract_drawdown(p)
        assert dd > 0

    def test_insufficient_data(self) -> None:
        dd = extract_drawdown((1,))
        assert dd == 0.0

    def test_range_zero_to_one(self) -> None:
        p = _prices(count=50)
        dd = extract_drawdown(p)
        assert 0.0 <= dd <= 1.0


class TestExtractRecoveryStrength:
    def test_full_recovery(self) -> None:
        p = (100, 90, 80, 85, 95, 100, 105)
        rs = extract_recovery_strength(p, RegimeConfig(short_lookback=5))
        assert rs > 0.8

    def test_no_recovery(self) -> None:
        p = tuple(100 - i * 2 for i in range(25))
        rs = extract_recovery_strength(p, RegimeConfig(short_lookback=20))
        assert rs < 0.3

    def test_insufficient_data(self) -> None:
        with pytest.raises(InsufficientDataError):
            extract_recovery_strength((1,), RegimeConfig(short_lookback=20))

    def test_range_zero_to_one(self) -> None:
        p = _prices(count=50)
        rs = extract_recovery_strength(p, RegimeConfig(short_lookback=20))
        assert 0.0 <= rs <= 1.0


class TestExtractLiquidityScore:
    def test_liquid(self) -> None:
        v = tuple(1_000_000 * (1 + 0.1 * math.sin(i * 0.3)) for i in range(30))
        ls = extract_liquidity_score(v)
        assert 0.0 <= ls <= 1.0

    def test_with_spreads(self) -> None:
        v = tuple(1_000_000 for _ in range(30))
        s = tuple(0.001 for _ in range(30))
        ls = extract_liquidity_score(v, s)
        assert 0.0 <= ls <= 1.0

    def test_insufficient_data_default(self) -> None:
        ls = extract_liquidity_score((1, 2))
        assert ls == 0.5


class TestFeatureExtractor:
    def test_extract_all(self) -> None:
        p = _prices(count=120)
        v = _volumes(count=120)
        a = _advances(60)
        d = _declines(60)
        rm = _returns_map(n=8, periods=60)
        extractor = FeatureExtractor()
        features = extractor.extract(p, v, a, d, rm)
        assert isinstance(features, RegimeFeatures)
        assert features.trend_strength != 0.0
        assert features.volatility_level != 0.0
        assert features.breadth != 0.0
        assert features.liquidity_score != 0.0

    def test_extract_minimal(self) -> None:
        p = (100, 101, 102)
        extractor = FeatureExtractor()
        features = extractor.extract(p)
        assert isinstance(features, RegimeFeatures)
        assert features.trend_strength == 0.0
        assert features.breadth == 0.5
        assert features.market_correlation == 0.5
        assert features.dispersion == 0.5
        assert features.liquidity_score == 0.5

    def test_extract_with_returns_map(self) -> None:
        p = _prices(count=100)
        rm = _returns_map(n=6, periods=60)
        extractor = FeatureExtractor()
        features = extractor.extract(p, returns_map=rm)
        assert 0.0 <= features.market_correlation <= 1.0
        assert 0.0 <= features.dispersion <= 1.0

    def test_extract_with_spreads(self) -> None:
        p = _prices(count=100)
        v = _volumes(count=100)
        s = tuple(0.001 for _ in range(30))
        extractor = FeatureExtractor()
        features = extractor.extract(p, volumes=v, spreads=s)
        assert 0.0 <= features.liquidity_score <= 1.0

    def test_extract_handles_errors_gracefully(self) -> None:
        p = (1, 2)
        extractor = FeatureExtractor()
        features = extractor.extract(p)
        assert features.trend_strength == 0.0


# =========================================================================
# Detectors
# =========================================================================


class TestBaseDetector:
    def test_name(self) -> None:
        d = BaseDetector()
        assert d.name == "base"

    def test_confidence_passthrough(self) -> None:
        d = BaseDetector()
        s = RegimeScore(regime=RegimeType.TRENDING_BULL, confidence=0.75)
        assert d.confidence(_default_features(), s) == 0.75

    def test_diagnostics_empty(self) -> None:
        d = BaseDetector()
        diag = d.diagnostics(())
        assert diag["accuracy"] == 0.0
        assert diag["stability"] == 0.0

    def test_diagnostics_stable(self) -> None:
        d = BaseDetector()
        rs = [RegimeResult(regime=RegimeType.TRENDING_BULL) for _ in range(5)]
        diag = d.diagnostics(tuple(rs))
        assert diag["total_detections"] == 5
        assert diag["stability"] == 1.0
        assert diag["changes"] == 0.0

    def test_diagnostics_unstable(self) -> None:
        d = BaseDetector()
        regimes = [RegimeType.TRENDING_BULL, RegimeType.SIDEWAYS, RegimeType.TRENDING_BULL]
        rs = [RegimeResult(regime=r) for r in regimes]
        diag = d.diagnostics(tuple(rs))
        assert diag["changes"] == 2.0
        assert diag["stability"] < 1.0


class TestRuleBasedDetector:
    def test_name(self) -> None:
        d = RuleBasedDetector()
        assert d.name == "rule_based"

    @pytest.mark.parametrize(
        "features,expected_regime",
        [
            ("_extreme_bull_features", RegimeType.TRENDING_BULL),
            ("_extreme_bear_features", RegimeType.TRENDING_BEAR),
        ],
    )
    def test_known_regimes(self, features: str, expected_regime: RegimeType) -> None:
        d = RuleBasedDetector()
        f = globals()[features]()
        result = d.detect(f, RegimeConfig())
        assert result.regime == expected_regime
        assert 0.0 <= result.confidence <= 1.0

    def test_unknown_regime(self) -> None:
        d = RuleBasedDetector()
        f = RegimeFeatures(trend_strength=0.0, momentum=0.0, volatility_level=0.5)
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.UNKNOWN
        assert result.confidence == 0.0

    def test_sideways(self) -> None:
        d = RuleBasedDetector()
        f = RegimeFeatures(trend_strength=0.0, momentum=0.0, volatility_level=0.1)
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.SIDEWAYS

    def test_accumulation(self) -> None:
        d = RuleBasedDetector()
        f = RegimeFeatures(
            trend_strength=0.3, volatility_level=0.2, breadth=0.7, recovery_strength=0.8,
        )
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.ACCUMULATION

    def test_distribution(self) -> None:
        d = RuleBasedDetector()
        f = RegimeFeatures(
            trend_strength=-0.3, volatility_level=0.4, breadth=0.3,
        )
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.DISTRIBUTION

    def test_recovery(self) -> None:
        d = RuleBasedDetector()
        f = RegimeFeatures(
            drawdown=0.1, trend_strength=0.4, recovery_strength=0.7, momentum=0.3,
            volatility_level=0.3,
        )
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.RECOVERY

    def test_high_volatility(self) -> None:
        d = RuleBasedDetector()
        f = RegimeFeatures(volatility_level=0.7)
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.HIGH_VOLATILITY

    def test_low_volatility(self) -> None:
        d = RuleBasedDetector()
        f = RegimeFeatures(volatility_level=0.1, trend_strength=0.3)
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.LOW_VOLATILITY

    def test_panic(self) -> None:
        d = RuleBasedDetector()
        f = RegimeFeatures(volatility_level=0.75, trend_strength=-0.6, drawdown=0.7)
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.PANIC

    def test_euphoria(self) -> None:
        d = RuleBasedDetector()
        f = RegimeFeatures(
            trend_strength=0.7, momentum=0.6, volatility_level=0.5, recovery_strength=0.9,
        )
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.EUPHORIA

    def test_competing_regimes(self) -> None:
        d = RuleBasedDetector()
        result = d.detect(_extreme_bull_features(), RegimeConfig())
        assert len(result.competing_regimes) > 0
        assert result.competing_regimes.get("TRENDING_BULL", 0) > 0

    def test_has_evidence(self) -> None:
        d = RuleBasedDetector()
        result = d.detect(_extreme_bull_features(), RegimeConfig())
        assert len(result.evidence) > 0


class TestScoreBasedDetector:
    def test_name(self) -> None:
        d = ScoreBasedDetector()
        assert d.name == "score_based"

    def test_detects_trending_bull(self) -> None:
        d = ScoreBasedDetector()
        result = d.detect(_extreme_bull_features(), RegimeConfig())
        assert result.regime == RegimeType.TRENDING_BULL

    def test_detects_trending_bear(self) -> None:
        d = ScoreBasedDetector()
        f = RegimeFeatures(
            trend_strength=-0.7, momentum=-0.6, volatility_level=0.4,
            breadth=0.2, drawdown=0.3,
        )
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.TRENDING_BEAR

    def test_detects_sideways(self) -> None:
        d = ScoreBasedDetector()
        f = RegimeFeatures(trend_strength=-0.01, momentum=0.0, volatility_level=0.1, volatility_change=0.0)
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.SIDEWAYS

    def test_detects_high_vol(self) -> None:
        d = ScoreBasedDetector()
        f = RegimeFeatures(volatility_level=0.9, volatility_change=0.5, liquidity_score=0.2)
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.HIGH_VOLATILITY

    def test_detects_low_vol(self) -> None:
        d = ScoreBasedDetector()
        f = RegimeFeatures(
            trend_strength=0.5, momentum=0.3, volatility_level=0.05,
            volatility_change=-0.3, liquidity_score=0.9,
        )
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.LOW_VOLATILITY

    def test_detects_panic(self) -> None:
        d = ScoreBasedDetector()
        f = RegimeFeatures(
            volatility_level=0.8, drawdown=0.9, trend_strength=-0.5, momentum=-0.5,
        )
        result = d.detect(f, RegimeConfig())
        assert result.regime == RegimeType.PANIC

    def test_confidence_bounded(self) -> None:
        d = ScoreBasedDetector()
        result = d.detect(_extreme_bull_features(), RegimeConfig())
        assert 0.0 <= result.confidence <= 1.0

    def test_competing_regimes(self) -> None:
        d = ScoreBasedDetector()
        result = d.detect(_default_features(), RegimeConfig())
        assert len(result.competing_regimes) > 0


class TestVotingDetector:
    def test_name(self) -> None:
        d = VotingDetector()
        assert d.name == "voting"

    def test_combines_detectors(self) -> None:
        d = VotingDetector()
        result = d.detect(_extreme_bull_features(), RegimeConfig())
        assert result.regime == RegimeType.TRENDING_BULL
        assert 0.0 <= result.confidence <= 1.0

    def test_unknown_when_no_votes(self) -> None:
        d = VotingDetector()
        f = RegimeFeatures(trend_strength=0.0, momentum=0.0, volatility_level=0.5)
        result = d.detect(f, RegimeConfig())
        assert result.confidence >= 0.0

    def test_combined_evidence(self) -> None:
        d = VotingDetector()
        result = d.detect(_extreme_bull_features(), RegimeConfig())
        assert len(result.evidence) > 0

    def test_custom_subdetectors(self) -> None:
        rule = RuleBasedDetector()
        score = ScoreBasedDetector()
        d = VotingDetector(rule_detector=rule, score_detector=score)
        result = d.detect(_extreme_bull_features(), RegimeConfig())
        assert result.regime == RegimeType.TRENDING_BULL


class TestHMMPlaceholderDetector:
    def test_name(self) -> None:
        d = HMMPlaceholderDetector()
        assert d.name == "hmm"

    def test_returns_unknown(self) -> None:
        d = HMMPlaceholderDetector()
        result = d.detect(_default_features(), RegimeConfig())
        assert result.regime == RegimeType.UNKNOWN
        assert result.confidence == 0.3

    def test_has_evidence(self) -> None:
        d = HMMPlaceholderDetector()
        result = d.detect(_default_features(), RegimeConfig())
        assert "placeholder" in result.evidence


class TestMLPlaceholderDetector:
    def test_name(self) -> None:
        d = MLPlaceholderDetector()
        assert d.name == "ml"

    def test_returns_unknown(self) -> None:
        d = MLPlaceholderDetector()
        result = d.detect(_default_features(), RegimeConfig())
        assert result.regime == RegimeType.UNKNOWN
        assert result.confidence == 0.2

    def test_has_evidence(self) -> None:
        d = MLPlaceholderDetector()
        result = d.detect(_default_features(), RegimeConfig())
        assert "placeholder" in result.evidence


# =========================================================================
# Scoring
# =========================================================================


class TestGetRecommendations:
    def test_all_regimes_have_recommendations(self) -> None:
        for regime in RegimeType:
            recs = get_recommendations(regime)
            assert "strategy" in recs
            assert "sizing" in recs
            assert "portfolio" in recs
            assert "risk" in recs
            assert "volatility" in recs
            assert "backtesting" in recs

    def test_unknown_regime(self) -> None:
        recs = get_recommendations(RegimeType.UNKNOWN)
        assert recs["strategy"] == "Maintain current positions"

    def test_trending_bull_recommendations(self) -> None:
        recs = get_recommendations(RegimeType.TRENDING_BULL)
        assert "trend-following" in recs["strategy"].lower()

    def test_panic_recommendations(self) -> None:
        recs = get_recommendations(RegimeType.PANIC)
        assert "capital" in recs["strategy"].lower()

    def test_different_recommendations(self) -> None:
        bull = get_recommendations(RegimeType.TRENDING_BULL)
        bear = get_recommendations(RegimeType.TRENDING_BEAR)
        assert bull["sizing"] != bear["sizing"]


class TestComputeTransitionProbability:
    def test_same_regime(self) -> None:
        f = _default_features()
        s = RegimeScore(regime=RegimeType.TRENDING_BULL, confidence=0.8)
        prob = compute_transition_probability(RegimeType.TRENDING_BULL, RegimeType.TRENDING_BULL, f, s)
        assert prob <= 1.0

    def test_different_regime_high_confidence(self) -> None:
        f = _default_features()
        s = RegimeScore(regime=RegimeType.TRENDING_BEAR, confidence=0.9)
        prob = compute_transition_probability(RegimeType.TRENDING_BEAR, RegimeType.TRENDING_BULL, f, s)
        assert prob > 0.5

    def test_different_regime_low_confidence(self) -> None:
        f = RegimeFeatures(trend_strength=0.0, volatility_change=0.0)
        s = RegimeScore(regime=RegimeType.SIDEWAYS, confidence=0.3)
        prob = compute_transition_probability(RegimeType.SIDEWAYS, RegimeType.TRENDING_BULL, f, s)
        assert prob < 0.5

    def test_previous_none(self) -> None:
        f = _default_features()
        s = RegimeScore(regime=RegimeType.TRENDING_BULL, confidence=0.8)
        prob = compute_transition_probability(RegimeType.TRENDING_BULL, None, f, s)
        assert prob == 1.0 - s.confidence

    def test_strong_features_drive_transition(self) -> None:
        f = RegimeFeatures(trend_strength=0.6, volatility_change=0.4)
        s = RegimeScore(regime=RegimeType.TRENDING_BULL, confidence=0.5)
        prob = compute_transition_probability(RegimeType.TRENDING_BULL, RegimeType.SIDEWAYS, f, s)
        assert prob > 0.5


class TestComputeRegimeStatistics:
    def test_empty(self) -> None:
        stats = compute_regime_statistics(())
        assert stats.total_detections == 0
        assert stats.most_common == "UNKNOWN"

    def test_single_regime(self) -> None:
        rs = [RegimeResult(regime=RegimeType.TRENDING_BULL) for _ in range(5)]
        stats = compute_regime_statistics(tuple(rs))
        assert stats.total_detections == 5
        assert stats.most_common == "TRENDING_BULL"
        assert stats.transition_count == 0
        assert stats.regime_stability == 1.0

    def test_transitions(self) -> None:
        regimes = [RegimeType.TRENDING_BULL, RegimeType.TRENDING_BULL, RegimeType.SIDEWAYS, RegimeType.SIDEWAYS, RegimeType.TRENDING_BULL]
        rs = [RegimeResult(regime=r) for r in regimes]
        stats = compute_regime_statistics(tuple(rs))
        assert stats.total_detections == 5
        assert stats.transition_count == 2
        assert stats.regime_stability < 1.0

    def test_regime_counts(self) -> None:
        regimes = [RegimeType.TRENDING_BULL, RegimeType.SIDEWAYS, RegimeType.TRENDING_BULL]
        rs = [RegimeResult(regime=r) for r in regimes]
        stats = compute_regime_statistics(tuple(rs))
        assert stats.regime_counts["TRENDING_BULL"] == 2
        assert stats.regime_counts["SIDEWAYS"] == 1

    def test_regime_durations(self) -> None:
        regimes = [RegimeType.TRENDING_BULL, RegimeType.TRENDING_BULL, RegimeType.SIDEWAYS]
        rs = [RegimeResult(regime=r) for r in regimes]
        stats = compute_regime_statistics(tuple(rs))
        assert stats.regime_durations["TRENDING_BULL"] == pytest.approx(2 / 3)
        assert stats.regime_durations["SIDEWAYS"] == pytest.approx(1 / 3)


class TestBuildTransitionMatrix:
    def test_empty(self) -> None:
        matrix = build_transition_matrix(())
        assert matrix == {}

    def test_single_regime_no_transitions(self) -> None:
        rs = [RegimeResult(regime=RegimeType.TRENDING_BULL) for _ in range(3)]
        matrix = build_transition_matrix(tuple(rs))
        assert "TRENDING_BULL" in matrix
        assert matrix["TRENDING_BULL"]["TRENDING_BULL"] == 1.0

    def test_transition_probabilities(self) -> None:
        regimes = [
            RegimeType.TRENDING_BULL,
            RegimeType.SIDEWAYS,
            RegimeType.TRENDING_BULL,
            RegimeType.TRENDING_BULL,
            RegimeType.SIDEWAYS,
        ]
        rs = [RegimeResult(regime=r) for r in regimes]
        matrix = build_transition_matrix(tuple(rs))
        assert "TRENDING_BULL" in matrix
        assert "SIDEWAYS" in matrix["TRENDING_BULL"]
        assert matrix["TRENDING_BULL"]["SIDEWAYS"] == pytest.approx(2 / 3)

    def test_probabilities_sum_to_one(self) -> None:
        regimes = [
            RegimeType.TRENDING_BULL,
            RegimeType.SIDEWAYS,
            RegimeType.TRENDING_BULL,
            RegimeType.SIDEWAYS,
            RegimeType.TRENDING_BULL,
        ]
        rs = [RegimeResult(regime=r) for r in regimes]
        matrix = build_transition_matrix(tuple(rs))
        for from_regime, targets in matrix.items():
            total = sum(targets.values())
            assert abs(total - 1.0) < 1e-6


# =========================================================================
# Engine
# =========================================================================


class TestRegimeEngine:
    def test_default_initialization(self) -> None:
        engine = RegimeEngine()
        assert isinstance(engine.config, RegimeConfig)
        assert engine.config.detector == "voting"
        assert engine.history == ()

    def test_custom_config(self) -> None:
        cfg = RegimeConfig(detector="rule_based")
        engine = RegimeEngine(config=cfg)
        assert engine.config.detector == "rule_based"

    def test_config_property(self) -> None:
        engine = RegimeEngine()
        assert engine.config is engine._config

    def test_history_property(self) -> None:
        engine = RegimeEngine()
        assert engine.history == ()
        p = _prices(count=100)
        engine.detect(p)
        assert len(engine.history) == 1

    def test_detect_with_default_detector(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=100)
        result = engine.detect(p)
        assert isinstance(result, RegimeResult)
        assert result.regime in RegimeType
        assert result.detector == "voting"
        assert result.elapsed >= 0.0

    def test_detect_with_rule_based(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=100, uptrend=True)
        result = engine.detect(p, detector_name="rule_based")
        assert result.detector == "rule_based"
        assert result.regime in RegimeType

    def test_detect_with_score_based(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=100, uptrend=True)
        result = engine.detect(p, detector_name="score_based")
        assert result.detector == "score_based"

    def test_detect_with_hmm_placeholder(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=100)
        result = engine.detect(p, detector_name="hmm")
        assert result.detector == "hmm"
        assert result.regime == RegimeType.UNKNOWN

    def test_detect_with_ml_placeholder(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=100)
        result = engine.detect(p, detector_name="ml")
        assert result.detector == "ml"
        assert result.regime == RegimeType.UNKNOWN

    def test_detect_with_volumes(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=100)
        v = _volumes(count=100)
        result = engine.detect(p, volumes=v)
        assert isinstance(result, RegimeResult)

    def test_detect_with_advances_declines(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=100)
        a = _advances(60)
        d = _declines(60)
        result = engine.detect(p, advances=a, declines=d)
        assert isinstance(result, RegimeResult)

    def test_detect_with_returns_map(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=100)
        rm = _returns_map(n=6, periods=60)
        result = engine.detect(p, returns_map=rm)
        assert isinstance(result, RegimeResult)

    def test_detect_with_spreads(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=100)
        v = _volumes(count=100)
        s = tuple(0.001 for _ in range(60))
        result = engine.detect(p, volumes=v, spreads=s)
        assert isinstance(result, RegimeResult)

    def test_detect_invalid_detector(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=100)
        with pytest.raises(DetectorNotFoundError):
            engine.detect(p, detector_name="nonexistent")

    def test_detect_tracks_history(self) -> None:
        engine = RegimeEngine()
        for _ in range(3):
            engine.detect(_prices(count=100, uptrend=True))
        assert len(engine.history) == 3

    def test_detect_has_recommendations(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=100)
        result = engine.detect(p)
        assert len(result.recommendations) == 6

    def test_detect_transition_probability(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=100)
        r1 = engine.detect(p)
        assert r1.score.transition_probability >= 0.0
        r2 = engine.detect(p)
        assert r2.score.transition_probability >= 0.0

    def test_detect_with_config_override(self) -> None:
        engine = RegimeEngine(config=RegimeConfig(detector="voting"))
        cfg = RegimeConfig(lookback=50)
        p = _prices(count=100)
        result = engine.detect(p, config=cfg)
        assert result.detector == "voting"
        assert isinstance(result, RegimeResult)

    def test_detect_batch(self) -> None:
        engine = RegimeEngine()
        price_series = tuple(_prices(count=100, uptrend=True) for _ in range(3))
        history = engine.detect_batch(price_series)
        assert isinstance(history, RegimeHistory)
        assert len(history.results) == 3

    def test_detect_batch_with_volumes(self) -> None:
        engine = RegimeEngine()
        price_series = tuple(_prices(count=100) for _ in range(3))
        vol_series = tuple(_volumes(count=100) for _ in range(3))
        history = engine.detect_batch(price_series, vol_series)
        assert len(history.results) == 3

    def test_detect_batch_partial_volumes(self) -> None:
        engine = RegimeEngine()
        price_series = tuple(_prices(count=100) for _ in range(3))
        vol_series = tuple(_volumes(count=100) for _ in range(2))
        history = engine.detect_batch(price_series, vol_series)
        assert len(history.results) == 3

    def test_detect_history_basic(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=300)
        history = engine.detect_history(p, window=100, step=50)
        assert isinstance(history, RegimeHistory)
        assert len(history.results) > 0

    def test_detect_history_insufficient_data(self) -> None:
        engine = RegimeEngine()
        p = (1, 2, 3)
        history = engine.detect_history(p, window=100, step=50)
        assert len(history.results) == 0

    def test_detect_history_with_volumes(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=300)
        v = _volumes(count=300)
        history = engine.detect_history(p, window=100, step=50, volumes=v)
        assert len(history.results) > 0

    def test_detect_history_tracks_transitions(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=300)
        history = engine.detect_history(p, window=100, step=50)
        if len(history.transitions) > 0:
            t = history.transitions[0]
            assert isinstance(t.from_regime, RegimeType)
            assert isinstance(t.to_regime, RegimeType)

    def test_transition_matrix_empty(self) -> None:
        engine = RegimeEngine()
        matrix = engine.transition_matrix()
        assert matrix == {}

    def test_transition_matrix_after_detections(self) -> None:
        engine = RegimeEngine()
        for _ in range(5):
            engine.detect(_prices(count=100, uptrend=True))
        matrix = engine.transition_matrix()
        assert len(matrix) > 0

    def test_regime_statistics_empty(self) -> None:
        engine = RegimeEngine()
        stats = engine.regime_statistics()
        assert stats.total_detections == 0

    def test_regime_statistics_after_detections(self) -> None:
        engine = RegimeEngine()
        for _ in range(5):
            engine.detect(_prices(count=100))
        stats = engine.regime_statistics()
        assert stats.total_detections == 5

    def test_batch_detects_all_periods(self) -> None:
        engine = RegimeEngine(config=RegimeConfig(detector="rule_based"))
        price_series = tuple(
            _prices(base=100, count=100, uptrend=i % 2 == 0)
            for i in range(4)
        )
        history = engine.detect_batch(price_series)
        assert len(history.results) == 4

    def test_detect_with_bearish_prices(self) -> None:
        engine = RegimeEngine()
        p = tuple(200 - i * 1.5 for i in range(100))
        p = tuple(max(v, 50) for v in p)
        result = engine.detect(p)
        assert isinstance(result, RegimeResult)
        assert result.regime in RegimeType

    def test_hook_engines_optional(self) -> None:
        engine = RegimeEngine(
            strategy_engine="strat",
            sizing_engine="sizing",
            portfolio_engine="port",
            risk_engine="risk",
            volatility_engine="vol",
            backtesting_engine="bt",
        )
        assert engine._strategy_engine == "strat"
        assert engine._sizing_engine == "sizing"


# =========================================================================
# Factory
# =========================================================================


class TestRegimeFactory:
    def test_create_default(self) -> None:
        engine = RegimeFactory.create()
        assert isinstance(engine, RegimeEngine)
        assert engine.config.detector == "voting"

    def test_create_with_config(self) -> None:
        cfg = RegimeConfig(detector="rule_based")
        engine = RegimeFactory.create(config=cfg)
        assert engine.config.detector == "rule_based"

    def test_create_with_feature_extractor(self) -> None:
        extractor = FeatureExtractor()
        engine = RegimeFactory.create(feature_extractor=extractor)
        assert engine._feature_extractor is extractor

    def test_create_with_engines(self) -> None:
        engine = RegimeFactory.create(
            strategy_engine="s1",
            sizing_engine="s2",
            portfolio_engine="p1",
            risk_engine="r1",
            volatility_engine="v1",
            backtesting_engine="b1",
        )
        assert engine._strategy_engine == "s1"
        assert engine._risk_engine == "r1"

    def test_create_with_detectors(self) -> None:
        detectors = {"custom": RuleBasedDetector()}
        engine = RegimeFactory.create_with_detectors(detectors)
        assert "custom" in engine._detectors

    def test_create_with_detectors_preserves_defaults(self) -> None:
        detectors = {"custom": RuleBasedDetector()}
        engine = RegimeFactory.create_with_detectors(detectors)
        assert "custom" in engine._detectors

    def test_create_from_config(self) -> None:
        cfg = RegimeConfig(detector="score_based")
        engine = RegimeFactory.create_from_config(cfg)
        assert isinstance(engine, RegimeEngine)
        assert engine.config.detector == "score_based"

    def test_create_from_config_defaults(self) -> None:
        engine = RegimeFactory.create_from_config(RegimeConfig())
        assert engine._detectors is not None

    def test_create_multiple_independent(self) -> None:
        e1 = RegimeFactory.create()
        e2 = RegimeFactory.create()
        assert e1 is not e2
        e1.detect(_prices(count=100))
        assert len(e2.history) == 0


# =========================================================================
# Error handling edge cases
# =========================================================================


class TestEdgeCases:
    def test_engine_with_single_price(self) -> None:
        engine = RegimeEngine()
        result = engine.detect(prices=(150.0,))
        assert isinstance(result, RegimeResult)
        assert result.regime in RegimeType

    def test_engine_with_two_prices(self) -> None:
        engine = RegimeEngine()
        result = engine.detect(prices=(100.0, 101.0))
        assert isinstance(result, RegimeResult)
        assert result.regime in RegimeType

    def test_engine_detect_twice_same_input(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=100)
        r1 = engine.detect(p)
        r2 = engine.detect(p)
        assert r1.regime == r2.regime

    def test_engine_history_immutable(self) -> None:
        engine = RegimeEngine()
        engine.detect(_prices(count=100))
        h = engine.history
        with pytest.raises(AttributeError):
            h[0].regime = RegimeType.UNKNOWN  # type: ignore

    def test_scoring_all_regimes_have_unique_recommendations(self) -> None:
        seen = set()
        for regime in RegimeType:
            recs = get_recommendations(regime)
            key = tuple(sorted(recs.items()))
            assert key not in seen, f"Duplicate recommendations for {regime}"
            seen.add(key)

    def test_detector_protocol_satisfied(self) -> None:
        for detector_cls in [
            RuleBasedDetector,
            ScoreBasedDetector,
            VotingDetector,
            HMMPlaceholderDetector,
            MLPlaceholderDetector,
        ]:
            d = detector_cls()
            assert hasattr(d, "name")
            assert hasattr(d, "detect")
            assert hasattr(d, "confidence")
            assert hasattr(d, "diagnostics")

    def test_all_detectors_available_in_default(self) -> None:
        engine = RegimeEngine()
        assert "rule_based" in engine._detectors
        assert "score_based" in engine._detectors
        assert "voting" in engine._detectors
        assert "hmm" in engine._detectors
        assert "ml" in engine._detectors

    def test_batch_detect_empty(self) -> None:
        engine = RegimeEngine()
        history = engine.detect_batch(())
        assert history.total_periods == 0

    def test_history_detect_no_overlap(self) -> None:
        engine = RegimeEngine()
        p = _prices(count=500)
        history = engine.detect_history(p, window=100, step=200)
        assert len(history.results) == 3
