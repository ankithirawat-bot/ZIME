"""
Anomaly detection engine.

Runs every registered anomaly detector over a sequence of bars and collects
the resulting :class:`Anomaly` objects. Five default detectors are provided
(negative prices, price spikes, impossible gaps, abnormal volume, stale data);
new detectors register without changing engine code.
"""

from __future__ import annotations

from collections.abc import Sequence
from statistics import median

from backend.data_quality.models import Anomaly, PriceBar
from backend.data_quality.registry import AnomalyDetector, RuleRegistry


def _detect_negative_prices(
    bars: Sequence[PriceBar], symbol: str, exchange: str, provider: str
) -> list[Anomaly]:
    out: list[Anomaly] = []
    for i, bar in enumerate(bars):
        for field in ("open", "high", "low", "close"):
            value = getattr(bar, field)
            if value != value or value <= 0:
                out.append(
                    Anomaly(
                        provider=provider, symbol=symbol, anomaly_type="negative_price",
                        severity="high",
                        description=f"{field} <= 0 on {bar.trade_date.isoformat()}",
                        date=bar.trade_date, index=i, value=value,
                    )
                )
                break
    return tuple(out)


def _detect_price_spikes(
    bars: Sequence[PriceBar], symbol: str, exchange: str, provider: str
) -> list[Anomaly]:
    out: list[Anomaly] = []
    ordered = sorted(bars, key=lambda b: b.trade_date)
    for i in range(1, len(ordered)):
        prev, cur = ordered[i - 1], ordered[i]
        if prev.close == prev.close and prev.close > 0:
            ret = (cur.close - prev.close) / prev.close
            if abs(ret) > 0.2:
                out.append(
                    Anomaly(
                        provider=provider, symbol=symbol, anomaly_type="price_spike",
                        severity="high",
                        description=f"Close return {ret:.2%} on {cur.trade_date.isoformat()}",
                        date=cur.trade_date, index=i, value=ret,
                    )
                )
    return tuple(out)


def _detect_impossible_gaps(
    bars: Sequence[PriceBar], symbol: str, exchange: str, provider: str
) -> list[Anomaly]:
    out: list[Anomaly] = []
    ordered = sorted(bars, key=lambda b: b.trade_date)
    for i in range(1, len(ordered)):
        prev, cur = ordered[i - 1], ordered[i]
        if prev.close == prev.close and prev.close > 0:
            gap = (cur.open - prev.close) / prev.close
            if abs(gap) > 0.5:
                out.append(
                    Anomaly(
                        provider=provider, symbol=symbol, anomaly_type="impossible_gap",
                        severity="medium",
                        description=f"Open gap {gap:.2%} vs prior close on {cur.trade_date.isoformat()}",
                        date=cur.trade_date, index=i, value=gap,
                    )
                )
    return tuple(out)


def _detect_abnormal_volume(
    bars: Sequence[PriceBar], symbol: str, exchange: str, provider: str
) -> list[Anomaly]:
    out: list[Anomaly] = []
    volumes = [b.volume for b in bars if b.volume == b.volume and b.volume >= 0]
    med = median(volumes) if volumes else 0.0
    for i, bar in enumerate(bars):
        if bar.volume != bar.volume or bar.volume < 0:
            continue
        if bar.volume == 0:
            out.append(
                Anomaly(
                    provider=provider, symbol=symbol, anomaly_type="abnormal_volume",
                    severity="low", description=f"Zero volume on {bar.trade_date.isoformat()}",
                    date=bar.trade_date, index=i, value=0.0,
                )
            )
        elif med > 0 and bar.volume > 10 * med:
            out.append(
                Anomaly(
                    provider=provider, symbol=symbol, anomaly_type="abnormal_volume",
                    severity="medium",
                    description=f"Volume {bar.volume:g} >> median {med:g} on {bar.trade_date.isoformat()}",
                    date=bar.trade_date, index=i, value=bar.volume,
                )
            )
    return tuple(out)


def _detect_stale_data(
    bars: Sequence[PriceBar], symbol: str, exchange: str, provider: str
) -> list[Anomaly]:
    out: list[Anomaly] = []
    ordered = sorted(bars, key=lambda b: b.trade_date)
    run = 1
    for i in range(1, len(ordered)):
        cur, prev = ordered[i], ordered[i - 1]
        if cur.open == prev.open and cur.high == prev.high and cur.low == prev.low and cur.close == prev.close:
            run += 1
            if run >= 3:
                out.append(
                    Anomaly(
                        provider=provider, symbol=symbol, anomaly_type="stale_data",
                        severity="medium",
                        description=f"{run} consecutive identical bars ending {cur.trade_date.isoformat()}",
                        date=cur.trade_date, index=i, value=float(run),
                    )
                )
        else:
            run = 1
    return tuple(out)


def _register_default_detectors(registry: RuleRegistry) -> None:
    defaults: dict[str, AnomalyDetector] = {
        "negative_price": _detect_negative_prices,
        "price_spike": _detect_price_spikes,
        "impossible_gap": _detect_impossible_gaps,
        "abnormal_volume": _detect_abnormal_volume,
        "stale_data": _detect_stale_data,
    }
    for name, detector in defaults.items():
        if name not in registry.anomaly_detectors():
            registry.register_anomaly_detector(name, detector)


class AnomalyDetectorEngine:
    """Runs registered anomaly detectors over bars."""

    def __init__(self, registry: RuleRegistry | None = None) -> None:
        self._registry = registry or RuleRegistry()
        _register_default_detectors(self._registry)

    def register_detector(self, name: str, detector: AnomalyDetector) -> None:
        """Register an additional anomaly detector."""
        self._registry.register_anomaly_detector(name, detector)

    def detect(
        self,
        bars: Sequence[PriceBar],
        symbol: str,
        exchange: str,
        provider: str,
    ) -> tuple[Anomaly, ...]:
        """Run all detectors, returning every detected anomaly."""
        anomalies: list[Anomaly] = []
        for detector in self._registry.anomaly_detectors().values():
            anomalies.extend(detector(bars, symbol, exchange, provider))
        return tuple(anomalies)
