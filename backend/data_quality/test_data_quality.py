"""
Data quality platform tests.

Covers validation rules, provider comparison, anomaly detection, confidence
scoring, report generation, the rule/detector registry, multi-provider flows
and edge cases.
"""

from __future__ import annotations

from datetime import date

import pytest

from backend.data_quality.anomaly_detector import (
    AnomalyDetectorEngine,
    _detect_abnormal_volume,
    _detect_impossible_gaps,
    _detect_negative_prices,
    _detect_price_spikes,
    _detect_stale_data,
)
from backend.data_quality.comparator import DataComparator, _relative_diff
from backend.data_quality.confidence import ConfidenceEngine
from backend.data_quality.exceptions import (
    DetectorNotFoundError,
    RuleNotFoundError,
    ValidationError,
)
from backend.data_quality.models import (
    Anomaly,
    PriceBar,
    ValidationRequest,
    ValidationResult,
)
from backend.data_quality.registry import RuleRegistry
from backend.data_quality.report import ReportGenerator
from backend.data_quality.validator import DataValidator, _is_invalid_ohlc


def _bar(day, o, h, lo, c, v, ac=None):
    return PriceBar(
        trade_date=date(2024, 1, day),
        open=o, high=h, low=lo, close=c, volume=v, adjusted_close=ac,
    )


def _request(bars, provider="A", as_of=None):
    return ValidationRequest(
        symbol="RELIANCE", exchange="NSE", provider=provider, bars=tuple(bars), as_of=as_of,
    )


class TestValidationRequest:
    def test_invalid_symbol(self):
        with pytest.raises(ValidationError):
            ValidationRequest(symbol="", exchange="NSE", provider="A", bars=())

    def test_auto_request_id(self):
        req = ValidationRequest(symbol="X", exchange="NSE", provider="A", bars=())
        assert req.request_id

    def test_none_bars_rejected(self):
        with pytest.raises(ValidationError):
            ValidationRequest(symbol="X", exchange="NSE", provider="A", bars=None)


class TestValidatorRules:
    def test_clean_bars_valid(self):
        bars = [_bar(d, 10, 11, 9, 10.5, 1000) for d in range(1, 6)]
        result = DataValidator().validate(_request(bars))
        assert result.is_valid
        assert result.issues == ()

    def test_missing_days(self):
        bars = [_bar(1, 10, 11, 9, 10, 1000), _bar(5, 10, 11, 9, 10, 1000)]
        result = DataValidator().validate(_request(bars))
        assert len(result.missing_days) == 3
        assert not result.is_valid

    def test_duplicate_rows(self):
        bars = [_bar(1, 10, 11, 9, 10, 1000), _bar(1, 10, 11, 9, 10, 1000)]
        result = DataValidator().validate(_request(bars))
        assert result.duplicate_rows == (1,)
        assert not result.is_valid

    def test_invalid_ohlc(self):
        bars = [_bar(1, 10, 9, 8, 10, 1000)]
        result = DataValidator().validate(_request(bars))
        assert result.invalid_ohlc == (0,)

    def test_invalid_volume_negative(self):
        bars = [_bar(1, 10, 11, 9, 10, -5)]
        result = DataValidator().validate(_request(bars))
        assert result.invalid_volume == (0,)

    def test_invalid_volume_nan(self):
        bars = [_bar(1, 10, 11, 9, 10, float("nan"))]
        result = DataValidator().validate(_request(bars))
        assert result.invalid_volume == (0,)

    def test_timestamp_order(self):
        bars = [_bar(2, 10, 11, 9, 10, 1000), _bar(1, 10, 11, 9, 10, 1000)]
        result = DataValidator().validate(_request(bars))
        assert result.timestamp_issues == (1,)

    def test_future_dates(self):
        future = date(2099, 1, 1)
        bars = [PriceBar(trade_date=future, open=10, high=11, low=9, close=10, volume=1000)]
        req = ValidationRequest(symbol="X", exchange="NSE", provider="A", bars=tuple(bars))
        result = DataValidator().validate(req)
        assert result.future_dates == (0,)

    def test_future_date_uses_as_of(self):
        bars = [PriceBar(trade_date=date(2030, 1, 1), open=10, high=11, low=9, close=10, volume=1000)]
        req = ValidationRequest(
            symbol="X", exchange="NSE", provider="A", bars=tuple(bars), as_of=date(2035, 1, 1),
        )
        result = DataValidator().validate(req)
        assert result.future_dates == ()

    def test_register_extra_rule(self):
        validator = DataValidator()

        def always_flag(req):
            from backend.data_quality.models import Issue

            return [Issue(code="custom", message="flag", severity="low")]

        validator.register_rule("custom", always_flag)
        result = validator.validate(_request([_bar(1, 10, 11, 9, 10, 1000)]))
        assert any(i.code == "custom" for i in result.issues)


class TestIsInvalidOhlc:
    def test_valid(self):
        assert not _is_invalid_ohlc(_bar(1, 10, 11, 9, 10, 1000))

    def test_high_below_max(self):
        assert _is_invalid_ohlc(PriceBar(date(2024, 1, 1), 10, 9, 8, 10, 1000))

    def test_low_above_min(self):
        assert _is_invalid_ohlc(PriceBar(date(2024, 1, 1), 10, 12, 11, 10, 1000))

    def test_high_below_low(self):
        assert _is_invalid_ohlc(PriceBar(date(2024, 1, 1), 10, 9, 10, 10, 1000))

    def test_non_positive(self):
        assert _is_invalid_ohlc(PriceBar(date(2024, 1, 1), 0, 11, 9, 10, 1000))

    def test_nan(self):
        assert _is_invalid_ohlc(
            PriceBar(date(2024, 1, 1), float("nan"), 11, 9, 10, 1000)
        )


class TestComparator:
    def test_single_provider(self):
        comp = DataComparator().compare(
            "RELIANCE", "NSE", {"A": tuple(_bar(d, 10, 11, 9, 10, 1000) for d in range(1, 5))}
        )
        assert comp.providers == ("A",)
        assert comp.agreement_score == 100.0
        assert comp.ohlc_diffs == () and comp.volume_diffs == ()

    def test_ohlc_and_volume_diffs(self):
        a = tuple(_bar(d, 10, 11, 9, 10, 1000) for d in range(1, 4))
        b = tuple(
            [
                _bar(1, 10, 11, 9, 10, 1000),
                _bar(2, 10, 11, 9, 12, 1000),
                _bar(3, 10, 11, 9, 10, 5000),
            ]
        )
        comp = DataComparator().compare("RELIANCE", "NSE", {"A": a, "B": b})
        close_diffs = [d for d in comp.ohlc_diffs if d.metric == "close"]
        volume_diffs = list(comp.volume_diffs)
        assert close_diffs and close_diffs[0].value_b == 12
        assert volume_diffs and volume_diffs[0].value_b == 5000

    def test_within_tolerance_no_diff(self):
        a = tuple(_bar(d, 10, 11, 9, 10.00, 1000) for d in range(1, 4))
        b = tuple(_bar(d, 10, 11, 9, 10.005, 1000) for d in range(1, 4))
        comp = DataComparator().compare("RELIANCE", "NSE", {"A": a, "B": b})
        assert comp.ohlc_diffs == ()

    def test_missing_records_and_date_mismatch(self):
        a = tuple(_bar(d, 10, 11, 9, 10, 1000) for d in range(1, 4))
        b = tuple(_bar(d, 10, 11, 9, 10, 1000) for d in range(2, 5))
        comp = DataComparator().compare("RELIANCE", "NSE", {"A": a, "B": b})
        assert date(2024, 1, 1) in comp.date_mismatches
        assert date(2024, 1, 4) in comp.date_mismatches
        assert any(mr.provider == "A" and mr.date == date(2024, 1, 4) for mr in comp.missing_records)
        assert any(mr.provider == "B" and mr.date == date(2024, 1, 1) for mr in comp.missing_records)

    def test_corporate_action_divergence(self):
        a = tuple(_bar(d, 10, 11, 9, 100, 1000) for d in range(1, 4))
        b = tuple(_bar(d, 10, 11, 9, 50, 1000) for d in range(1, 4))
        comp = DataComparator().compare("RELIANCE", "NSE", {"A": a, "B": b})
        assert comp.corporate_action_divergence
        assert comp.corporate_action_divergence[0].ratio == 0.5

    def test_no_divergence_when_below_threshold(self):
        a = tuple(_bar(d, 10, 11, 9, 100, 1000) for d in range(1, 4))
        b = tuple(_bar(d, 10, 11, 9, 110, 1000) for d in range(1, 4))
        comp = DataComparator().compare("RELIANCE", "NSE", {"A": a, "B": b})
        assert comp.corporate_action_divergence == ()

    def test_nan_values_skipped(self):
        a = tuple(_bar(d, 10, 11, 9, 100, 1000) for d in range(1, 4))
        b = tuple(
            [
                _bar(1, 10, 11, 9, 100, 1000),
                _bar(2, 10, 11, 9, float("nan"), 1000),
                _bar(3, 10, 11, 9, 100, 1000),
            ]
        )
        comp = DataComparator().compare("RELIANCE", "NSE", {"A": a, "B": b})
        assert all(d.value_b == d.value_b for c in comp.ohlc_diffs for d in [c])

    def test_agreement_score_identical(self):
        a = tuple(_bar(d, 10, 11, 9, 100, 1000) for d in range(1, 5))
        b = tuple(_bar(d, 10, 11, 9, 100, 1000) for d in range(1, 5))
        comp = DataComparator().compare("RELIANCE", "NSE", {"A": a, "B": b})
        assert comp.agreement_score == 100.0

    def test_agreement_score_partial_nan(self):
        a = tuple(_bar(d, 10, 11, 9, 100, 1000) for d in range(1, 4))
        b = tuple(_bar(d, 10, 11, 9, float("nan"), 1000) for d in range(1, 4))
        comp = DataComparator().compare("RELIANCE", "NSE", {"A": a, "B": b})
        assert comp.agreement_score == 100.0

    def test_agreement_score_disjoint_dates(self):
        a = tuple(_bar(d, 10, 11, 9, 100, 1000) for d in range(1, 3))
        b = tuple(_bar(d, 10, 11, 9, 100, 1000) for d in range(5, 7))
        comp = DataComparator().compare("RELIANCE", "NSE", {"A": a, "B": b})
        assert comp.agreement_score == 100.0
        assert comp.date_mismatches

    def test_agreement_score_zero_mean(self):
        a = tuple(_bar(d, 0, 0, 0, 0, 1000) for d in range(1, 4))
        b = tuple(_bar(d, 0, 0, 0, 0, 1000) for d in range(1, 4))
        comp = DataComparator().compare("RELIANCE", "NSE", {"A": a, "B": b})
        assert comp.agreement_score == 100.0


class TestRelativeDiff:
    def test_normal(self):
        assert _relative_diff(110, 100) == pytest.approx(10 / 110)

    def test_zero_denominator(self):
        assert _relative_diff(0, 0) == 0.0


class TestAnomalyDetectors:
    def test_negative_price(self):
        bars = [_bar(1, -5, 11, 9, 10, 1000)]
        anomalies = _detect_negative_prices(bars, "X", "NSE", "A")
        assert anomalies and anomalies[0].anomaly_type == "negative_price"

    def test_negative_price_nan(self):
        bars = [PriceBar(date(2024, 1, 1), float("nan"), 11, 9, 10, 1000)]
        anomalies = _detect_negative_prices(bars, "X", "NSE", "A")
        assert anomalies

    def test_price_spike(self):
        bars = [_bar(1, 100, 101, 99, 100, 1000), _bar(2, 100, 101, 99, 130, 1000)]
        anomalies = _detect_price_spikes(bars, "X", "NSE", "A")
        assert any(a.anomaly_type == "price_spike" for a in anomalies)

    def test_no_price_spike(self):
        bars = [_bar(1, 100, 101, 99, 100, 1000), _bar(2, 100, 101, 99, 102, 1000)]
        anomalies = _detect_price_spikes(bars, "X", "NSE", "A")
        assert anomalies == ()

    def test_impossible_gap(self):
        bars = [_bar(1, 100, 101, 99, 100, 1000), _bar(2, 200, 201, 199, 200, 1000)]
        anomalies = _detect_impossible_gaps(bars, "X", "NSE", "A")
        assert any(a.anomaly_type == "impossible_gap" for a in anomalies)

    def test_abnormal_volume_zero(self):
        bars = [_bar(1, 10, 11, 9, 10, 0)]
        anomalies = _detect_abnormal_volume(bars, "X", "NSE", "A")
        assert any(a.anomaly_type == "abnormal_volume" and a.value == 0.0 for a in anomalies)

    def test_abnormal_volume_spike(self):
        bars = [_bar(d, 10, 11, 9, 10, 1000 if d != 3 else 100000) for d in range(1, 6)]
        anomalies = _detect_abnormal_volume(bars, "X", "NSE", "A")
        assert any(a.anomaly_type == "abnormal_volume" and a.value == 100000 for a in anomalies)

    def test_stale_data(self):
        bars = [_bar(d, 10, 11, 9, 10, 1000) for d in range(1, 5)]
        anomalies = _detect_stale_data(bars, "X", "NSE", "A")
        assert any(a.anomaly_type == "stale_data" for a in anomalies)

    def test_no_stale_data(self):
        bars = [_bar(d, 10 + d, 11 + d, 9 + d, 10 + d, 1000) for d in range(1, 5)]
        anomalies = _detect_stale_data(bars, "X", "NSE", "A")
        assert anomalies == ()


class TestAnomalyEngine:
    def test_detect_all(self):
        bars = [_bar(1, -1, 11, 9, 10, 0)]
        anomalies = AnomalyDetectorEngine().detect(bars, "X", "NSE", "A")
        assert len(anomalies) >= 2

    def test_register_custom_detector(self):
        engine = AnomalyDetectorEngine()
        engine.register_detector(
            "custom",
            lambda bars, s, e, p: [Anomaly(p, s, "custom", "low", "x")],
        )
        anomalies = engine.detect([_bar(1, 10, 11, 9, 10, 1000)], "X", "NSE", "A")
        assert any(a.anomaly_type == "custom" for a in anomalies)

    def test_empty_bars(self):
        assert AnomalyDetectorEngine().detect((), "X", "NSE", "A") == ()


class TestConfidence:
    def test_clean_high_confidence(self):
        result = ValidationResult(
            symbol="X", exchange="NSE", provider="A", missing_days=(), duplicate_rows=(),
            invalid_ohlc=(), invalid_volume=(), timestamp_issues=(), future_dates=(),
            issues=(), is_valid=True,
        )
        score = ConfidenceEngine().compute("X", "NSE", "A", result)
        assert score.score == 100.0

    def test_issues_reduce_score(self):
        from backend.data_quality.models import Issue

        result = ValidationResult(
            symbol="X", exchange="NSE", provider="A", missing_days=(), duplicate_rows=(),
            invalid_ohlc=(0,), invalid_volume=(), timestamp_issues=(), future_dates=(),
            issues=(Issue(code="invalid_ohlc", message="x", index=0, severity="high"),),
            is_valid=False,
        )
        score = ConfidenceEngine().compute("X", "NSE", "A", result)
        assert score.score < 100.0
        assert score.components["validation"] == 75.0

    def test_comparison_agreement(self):
        result = ValidationResult(
            symbol="X", exchange="NSE", provider="A", missing_days=(), duplicate_rows=(),
            invalid_ohlc=(), invalid_volume=(), timestamp_issues=(), future_dates=(),
            issues=(), is_valid=True,
        )
        comp = DataComparator().compare(
            "X", "NSE",
            {"A": tuple(_bar(d, 10, 11, 9, 100, 1000) for d in range(1, 5)),
             "B": tuple(_bar(d, 10, 11, 9, 100, 1000) for d in range(1, 5))},
        )
        score = ConfidenceEngine().compute("X", "NSE", "A", result, comparison=comp)
        assert score.components["comparison"] == 100.0

    def test_reliability_weighting(self):
        result = ValidationResult(
            symbol="X", exchange="NSE", provider="A", missing_days=(), duplicate_rows=(),
            invalid_ohlc=(), invalid_volume=(), timestamp_issues=(), future_dates=(),
            issues=(), is_valid=True,
        )
        score = ConfidenceEngine().compute(
            "X", "NSE", "A", result, provider_reliability=0.5, historical_reliability=0.5,
        )
        assert score.components["reliability"] == 50.0

    def test_zero_weights_raises(self):
        with pytest.raises(ValueError):
            ConfidenceEngine(0.0, 0.0, 0.0)


class TestReport:
    def test_generate_with_recommendations(self):
        validator = DataValidator()
        req = _request([_bar(1, 10, 9, 8, 10, -5), _bar(3, 10, 11, 9, 10, 1000)])
        validation = validator.validate(req)
        engine = AnomalyDetectorEngine()
        anomalies = engine.detect(req.bars, req.symbol, req.exchange, req.provider)
        score = ConfidenceEngine().compute(req.symbol, req.exchange, req.provider, validation)
        report = ReportGenerator().generate(req, validation, score, anomalies)
        assert report.issues
        assert report.recommendations
        assert "confidence" in report.summary
        assert any("invalid volume" in r.lower() for r in report.recommendations)

    def test_generate_clean(self):
        req = _request([_bar(d, 10, 11, 9, 10, 1000) for d in range(1, 4)])
        validation = DataValidator().validate(req)
        score = ConfidenceEngine().compute(req.symbol, req.exchange, req.provider, validation)
        report = ReportGenerator().generate(req, validation, score)
        assert report.recommendations == ("Data passes all quality checks.",)

    def test_generate_full_issue_spectrum(self):
        from backend.data_quality.models import Anomaly as _Anomaly

        req = ValidationRequest(
            symbol="X", exchange="NSE", provider="A", as_of=date(2024, 1, 3),
            bars=(
                _bar(1, 10, 11, 9, 10, 1000),
                _bar(1, 10, 11, 9, 10, 1000),
                PriceBar(date(2024, 1, 10), 10, 11, 9, 10, 1000),
                _bar(2, 10, 11, 9, 10, 1000),
            ),
        )
        validation = DataValidator().validate(req)
        assert validation.duplicate_rows and validation.future_dates and validation.timestamp_issues

        comp = DataComparator().compare(
            "X", "NSE",
            {"A": tuple(_bar(d, 10, 11, 9, 100, 1000) for d in range(1, 4)),
             "B": tuple(_bar(d, 10, 11, 9, 50, 1000) for d in range(1, 4))},
        )
        score = ConfidenceEngine().compute("X", "NSE", "A", validation, comparison=comp)
        anomalies = (_Anomaly(provider="A", symbol="X", anomaly_type="price_spike",
                              severity="high", description="x"),)
        report = ReportGenerator().generate(req, validation, score, anomalies, comp)
        assert report.summary["agreement_score"] == comp.agreement_score
        rec_text = " ".join(report.recommendations)
        assert "duplicate" in rec_text
        assert "future-dated" in rec_text
        assert "out-of-order" in rec_text
        assert "price_spike" in rec_text
        assert "corporate-action" in rec_text


class TestRegistry:
    def test_validation_rule_register_get(self):
        reg = RuleRegistry()
        reg.register_validation_rule("r", lambda req: [])
        assert reg.is_registered("r")
        assert reg.get_validation_rule("r") is not None
        assert "r" in reg.validation_rules()

    def test_validation_rule_missing(self):
        with pytest.raises(RuleNotFoundError):
            RuleRegistry().get_validation_rule("nope")

    def test_detector_register_get(self):
        reg = RuleRegistry()
        reg.register_anomaly_detector("d", lambda bars, s, e, p: [])
        assert reg.get_anomaly_detector("d") is not None
        assert "d" in reg.anomaly_detectors()

    def test_detector_missing(self):
        with pytest.raises(DetectorNotFoundError):
            RuleRegistry().get_anomaly_detector("nope")

    def test_rules_copy_isolated(self):
        reg = RuleRegistry()
        reg.register_validation_rule("r", lambda req: [])
        copy = reg.validation_rules()
        copy["r2"] = lambda req: []
        assert "r2" not in reg.validation_rules()


class TestMultiProviderFlow:
    def test_end_to_end(self):
        def _series():
            return tuple(
                _bar(d, 100 + d - 1, 100 + d + 1, 100 + d - 2, 100 + d, 1000)
                for d in range(1, 6)
            )

        provider_bars = {"Yahoo": _series(), "Upstox": _series()}
        validator = DataValidator()
        comparator = DataComparator()
        anomaly_engine = AnomalyDetectorEngine()
        confidence = ConfidenceEngine()

        results = {}
        anomalies_all = []
        for provider, bars in provider_bars.items():
            req = ValidationRequest(symbol="RELIANCE", exchange="NSE", provider=provider, bars=bars)
            vr = validator.validate(req)
            results[provider] = vr
            anomalies_all.extend(anomaly_engine.detect(bars, "RELIANCE", "NSE", provider))

        comparison = comparator.compare("RELIANCE", "NSE", provider_bars)
        assert comparison.agreement_score == 100.0

        score = confidence.compute(
            "RELIANCE", "NSE", "Yahoo", results["Yahoo"], comparison=comparison,
        )
        assert score.score == 100.0

        report = ReportGenerator().generate(
            ValidationRequest(symbol="RELIANCE", exchange="NSE", provider="Yahoo", bars=provider_bars["Yahoo"]),
            results["Yahoo"], score, tuple(anomalies_all), comparison,
        )
        assert report.summary["agreement_score"] == 100.0
        assert report.recommendations == ("Data passes all quality checks.",)
