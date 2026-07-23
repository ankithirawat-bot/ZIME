"""Adapter bridging Reporting & Analytics workspace to backend reporting capabilities."""

from __future__ import annotations

from frontend.viewmodels.reporting_viewmodels import (
    AnalyticsSummary,
    ChartSeries,
    PerformanceMetric,
    ReportingViewModel,
    ReportStatus,
    StrategyComparison,
)


class ReportingAdapter:
    """Adapter providing deterministic sample data or live converted data.

    - Queries via controller.get_reporting_engine()
    - Never exposes backend models directly
    - Returns immutable dataclasses
    """

    def __init__(self, controller) -> None:
        self._controller = controller

    # Sample data interface

    def sample_view_model(self) -> ReportingViewModel:
        analytics = AnalyticsSummary(
            portfolio_return=14.3,
            benchmark_return=8.9,
            alpha=5.4,
            beta=0.95,
            sharpe_ratio=0.87,
            max_drawdown=-11.8,
        )
        metrics = PerformanceMetric(
            cagr=12.8,
            annual_return=14.3,
            volatility=13.9,
            sortino_ratio=0.96,
            calmar_ratio=1.09,
            information_ratio=1.21,
            profit_factor=1.42,
            win_rate=58.2,
        )
        strategies = [
            StrategyComparison(strategy_return=22.1, sharpe=0.92, drawdown=-14.5, win_rate=59.1, trades=42),
            StrategyComparison(strategy_return=10.3, sharpe=0.67, drawdown=-9.2, win_rate=54.5, trades=37),
            StrategyComparison(strategy_return=8.7, sharpe=0.58, drawdown=-8.4, win_rate=56.4, trades=51),
            StrategyComparison(strategy_return=18.5, sharpe=0.83, drawdown=-12.8, win_rate=61.5, trades=48),
        ]
        charts = [
            ChartSeries("Equity", [(1, 100), (2, 112), (3, 108), (4, 118), (5, 124), (6, 131), (7, 139)]),
            ChartSeries("Monthly", [(1, 1.2), (2, -0.5), (3, 2.1), (4, 3.0), (5, -1.3), (6, 0.8), (7, 1.5)]),
            ChartSeries("Drawdown", [(1, -1.0), (2, -3.2), (3, -2.1), (4, -5.4), (5, -4.1), (6, -7.8), (7, -6.2)]),
        ]
        status = ReportStatus(
            backend_status="ready",
            data_status="healthy",
            last_refresh_utc=None,
            available_reports=[
                "Portfolio Snapshot",
                "Strategy Comparison",
                "Risk Metrics",
                "Trade Blotter",
            ],
            error=None,
        )
        return ReportingViewModel(
            analytics=analytics,
            metrics=metrics,
            strategies=strategies,
            charts=charts,
            status=status,
            is_refreshing=False,
            last_refresh_at_utc=None,
            controller_status=self._controller.status,
        )

    # Live data interface -- only called when backend available

    def load_view_model(self) -> ReportingViewModel:
        controller = self._controller
        try:
            engine = controller.get_reporting_engine()
            reports = engine.query_reports()
            if not reports:
                # Fallback to sample
                return self.sample_view_model()

            # TODO: Map backend schema to ViewModels here (Issue to follow sprint)
            # Placeholder return for architecture compliance — adapter returns immutable dataclass
            return self.sample_view_model()
        except Exception as exc:
            # On failure, still return deterministic sample data with error status
            vm = self.sample_view_model()
            object.__setattr__(
                vm,
                "status",
                ReportStatus(
                    backend_status="error",
                    data_status="stale",
                    last_refresh_utc=None,
                    available_reports=list(getattr(exc, "reports", []) or []),
                    error=str(exc)[:200],
                ),
            )
            object.__setattr__(vm, "is_refreshing", False)
            object.__setattr__(vm, "controller_status", "running" if self._controller.is_started else "stopped")
            return vm
