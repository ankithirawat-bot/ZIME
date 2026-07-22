"""
Benchmarks comparing sequential vs parallel analytics execution.

Run with::

    pytest backend/analytics/benchmarks/ -v
"""

from __future__ import annotations

import time
from datetime import date, timedelta

from backend.analytics.models import AnalyticsContext, MarketBar
from backend.analytics.pipeline import AnalyticsPipeline

# ---------------------------------------------------------------------------
# Helpers — build a context with realistic bar counts
# ---------------------------------------------------------------------------

def _context(bar_count: int) -> AnalyticsContext:
    """Build an AnalyticsContext with *bar_count* bars."""
    bars = tuple(
        MarketBar(
            trade_date=date(2024, 1, 1) + timedelta(days=i),
            open=float(100 + (i % 5)),
            high=float(101 + (i % 5)),
            low=float(99 + (i % 5)),
            close=float(100 + (i % 5)),
            volume=1_000_000.0,
        )
        for i in range(bar_count)
    )
    return AnalyticsContext(symbol="BENCH", exchange="NSE", prices=bars)


# ---------------------------------------------------------------------------
# Correctness — results must match across strategies
# ---------------------------------------------------------------------------

class TestCorrectness:
    """Verify parallel execution produces identical results."""

    def test_results_identical(self) -> None:
        ctx = _context(252)
        seq = AnalyticsPipeline(execution_strategy="sequential")
        par = AnalyticsPipeline(execution_strategy="parallel")

        seq_r = seq.run(ctx)
        par_r = par.run(ctx)

        assert seq_r.execution_order == par_r.execution_order
        assert seq_r.facts.keys() == par_r.facts.keys()

        for name in seq_r.facts:
            s = seq_r.facts[name]
            p = par_r.facts[name]
            assert s.state == p.state
            assert s.confidence == p.confidence
            assert s.evidence == p.evidence

        assert seq_r.report.success_count == par_r.report.success_count
        assert seq_r.report.failure_count == par_r.report.failure_count

    def test_execution_order_is_registry_order(self) -> None:
        ctx = _context(60)
        pipe = AnalyticsPipeline(execution_strategy="parallel")
        r = pipe.run(ctx)
        assert r.execution_order == (
            "Trend", "Momentum", "Volume", "Relative Strength", "Volatility",
        )


# ---------------------------------------------------------------------------
# Benchmarks — manual timing
# ---------------------------------------------------------------------------

class TestExecutionTime:
    """Measure and compare execution time per strategy."""

    BAR_COUNTS = [60, 252, 1000]

    def _measure(
        self,
        strategy: str,
        bar_count: int,
        iterations: int = 5,
    ) -> float:
        ctx = _context(bar_count)
        pipe = AnalyticsPipeline(execution_strategy=strategy)
        # warm-up
        pipe.run(ctx)
        total = 0.0
        for _ in range(iterations):
            start = time.perf_counter()
            pipe.run(ctx)
            total += time.perf_counter() - start
        return total / iterations

    def test_benchmark_60_bars(self) -> None:
        t_seq = self._measure("sequential", 60)
        t_par = self._measure("parallel", 60)
        print(f"\n  60 bars — sequential={t_seq*1000:.3f}ms  parallel={t_par*1000:.3f}ms")
        # Results must be correct regardless of timing
        assert t_seq > 0
        assert t_par > 0

    def test_benchmark_252_bars(self) -> None:
        t_seq = self._measure("sequential", 252)
        t_par = self._measure("parallel", 252)
        print(f"\n  252 bars — sequential={t_seq*1000:.3f}ms  parallel={t_par*1000:.3f}ms")

    def test_benchmark_1000_bars(self) -> None:
        t_seq = self._measure("sequential", 1000)
        t_par = self._measure("parallel", 1000)
        print(f"\n  1000 bars — sequential={t_seq*1000:.3f}ms  parallel={t_par*1000:.3f}ms")
