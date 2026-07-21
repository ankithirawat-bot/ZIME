"""
Provider comparator.

Compares OHLCV bars across multiple providers for the same instrument,
detecting OHLC/volume differences, missing records, date mismatches and
suspected corporate-action divergences, and producing an agreement score.
No provider is treated as authoritative.
"""

from __future__ import annotations

from datetime import date

from backend.data_quality.models import (
    ComparisonResult,
    CorporateActionDivergence,
    MissingRecord,
    PriceBar,
    ProviderComparison,
)


def _relative_diff(a: float, b: float) -> float:
    denom = max(abs(a), abs(b))
    if denom == 0:
        return 0.0
    return abs(a - b) / denom


class DataComparator:
    """Compares the same instrument across multiple providers."""

    def __init__(
        self,
        ohlc_tolerance: float = 0.01,
        volume_tolerance: float = 0.05,
        corporate_action_threshold: float = 0.25,
    ) -> None:
        self._ohlc_tolerance = ohlc_tolerance
        self._volume_tolerance = volume_tolerance
        self._ca_threshold = corporate_action_threshold

    def compare(
        self,
        symbol: str,
        exchange: str,
        provider_bars: dict[str, tuple[PriceBar, ...]],
    ) -> ProviderComparison:
        """Compare providers' bars for one instrument.

        Args:
            symbol:        Instrument symbol.
            exchange:      Exchange identifier.
            provider_bars: Mapping of provider name -> bars.

        Returns:
            ProviderComparison with diffs, missing records and agreement.
        """
        providers = tuple(sorted(provider_bars))
        by_date: dict[str, dict[date, PriceBar]] = {
            p: {b.trade_date: b for b in bars} for p, bars in provider_bars.items()
        }
        all_dates: set[date] = set()
        for mapping in by_date.values():
            all_dates.update(mapping)

        common = {d for d in all_dates if all(d in mapping for mapping in by_date.values())}
        date_mismatches = tuple(sorted(d for d in all_dates if d not in common))

        missing_records: list[MissingRecord] = []
        for provider, mapping in by_date.items():
            for d in sorted(all_dates - set(mapping)):
                missing_records.append(MissingRecord(provider=provider, date=d))

        ohlc_diffs: list[ComparisonResult] = []
        volume_diffs: list[ComparisonResult] = []
        ca_divergence: list[CorporateActionDivergence] = []

        metrics = (("open",), ("high",), ("low",), ("close",))
        for d in sorted(common):
            for metric in metrics:
                name = metric[0]
                values = {p: getattr(by_date[p][d], name) for p in providers}
                self._pairwise(
                    d, name, providers, values, self._ohlc_tolerance,
                    ohlc_diffs, volume_diffs, ca_divergence,
                )
            volume_values = {p: by_date[p][d].volume for p in providers}
            self._pairwise(
                d, "volume", providers, volume_values, self._volume_tolerance,
                ohlc_diffs, volume_diffs, ca_divergence,
            )

        agreement = self._agreement_score(providers, by_date, common)
        return ProviderComparison(
            symbol=symbol,
            exchange=exchange,
            providers=providers,
            ohlc_diffs=tuple(ohlc_diffs),
            volume_diffs=tuple(volume_diffs),
            missing_records=tuple(missing_records),
            date_mismatches=date_mismatches,
            corporate_action_divergence=tuple(ca_divergence),
            agreement_score=agreement,
        )

    def _pairwise(
        self,
        d: date,
        metric: str,
        providers: tuple[str, ...],
        values: dict[str, float],
        tolerance: float,
        ohlc_diffs: list[ComparisonResult],
        volume_diffs: list[ComparisonResult],
        ca_divergence: list[CorporateActionDivergence],
    ) -> None:
        for i in range(len(providers)):
            for j in range(i + 1, len(providers)):
                pa, pb = providers[i], providers[j]
                va, vb = values[pa], values[pb]
                if va != va or vb != vb:
                    continue
                diff = va - vb
                pct = _relative_diff(va, vb)
                is_volume = metric == "volume"
                if pct > tolerance:
                    result = ComparisonResult(
                        date=d, metric=metric, provider_a=pa, provider_b=pb,
                        value_a=va, value_b=vb, diff=diff, pct_diff=pct,
                    )
                    if is_volume:
                        volume_diffs.append(result)
                    else:
                        ohlc_diffs.append(result)
                if metric == "close" and pct > self._ca_threshold and pct <= 1.0:
                    ca_divergence.append(
                        CorporateActionDivergence(
                            date=d, provider_a=pa, provider_b=pb, ratio=vb / va if va else 0.0,
                            description=(
                                f"Close ratio {vb / va:.3f} between {pa} and {pb} "
                                f"exceeds corporate-action threshold"
                            ),
                        )
                    )

    def _agreement_score(
        self,
        providers: tuple[str, ...],
        by_date: dict[str, dict[date, PriceBar]],
        common: set[date],
    ) -> float:
        if len(providers) < 2 or not common:
            return 100.0
        spreads: list[float] = []
        for d in common:
            closes = [by_date[p][d].close for p in providers if by_date[p][d].close == by_date[p][d].close]
            if len(closes) < 2:
                continue
            mean = sum(closes) / len(closes)
            if mean == 0:
                continue
            spreads.append((max(closes) - min(closes)) / mean)
        if not spreads:
            return 100.0
        avg_spread = sum(spreads) / len(spreads)
        return max(0.0, min(100.0, 100.0 * (1.0 - avg_spread)))
