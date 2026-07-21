"""Backtesting reporting.

Generates reports from backtest results.
"""

from __future__ import annotations

from typing import Any

from backend.backtesting.models import (
    BacktestResult,
)


class BacktestReport:
    """Generates reports from backtest results.

    Provides structured access to backtest analysis data.
    """

    def __init__(self, result: BacktestResult) -> None:
        """Initialize the report.

        Args:
            result: Backtest result to report on.
        """
        self._result = result

    @property
    def result(self) -> BacktestResult:
        """Access the backtest result."""
        return self._result

    def trade_summary(self) -> dict[str, Any]:
        """Generate trade summary.

        Returns:
            Dictionary with trade summary data.
        """
        trades = self._result.trades
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "total_pnl": 0.0,
                "average_pnl": 0.0,
                "best_trade": None,
                "worst_trade": None,
            }

        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl < 0]

        return {
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "total_pnl": sum(t.pnl for t in trades),
            "average_pnl": sum(t.pnl for t in trades) / len(trades),
            "best_trade": max(trades, key=lambda t: t.pnl) if trades else None,
            "worst_trade": min(trades, key=lambda t: t.pnl) if trades else None,
        }

    def equity_curve_data(self) -> list[dict[str, Any]]:
        """Get equity curve data.

        Returns:
            List of dictionaries with equity curve points.
        """
        return [
            {
                "date": point.date.isoformat(),
                "equity": point.equity,
                "cash": point.cash,
            }
            for point in self._result.equity_curve
        ]

    def drawdown_curve_data(self) -> list[dict[str, Any]]:
        """Get drawdown curve data.

        Returns:
            List of dictionaries with drawdown points.
        """
        from backend.backtesting.metrics import calculate_drawdown_curve

        if not self._result.equity_curve:
            return []

        drawdowns = calculate_drawdown_curve(list(self._result.equity_curve))
        return [
            {
                "date": date.isoformat(),
                "drawdown": dd,
                "peak_equity": 0.0,
            }
            for date, dd in drawdowns
        ]

    def monthly_returns_data(self) -> list[dict[str, Any]]:
        """Get monthly returns data.

        Returns:
            List of dictionaries with monthly returns.
        """
        return [
            {"month": month, "return": ret}
            for month, ret in self._result.monthly_returns
        ]

    def yearly_returns_data(self) -> list[dict[str, Any]]:
        """Get yearly returns data.

        Returns:
            List of dictionaries with yearly returns.
        """
        return [
            {"year": year, "return": ret}
            for year, ret in self._result.yearly_returns
        ]

    def performance_summary(self) -> dict[str, Any]:
        """Get performance summary.

        Returns:
            Dictionary with key performance metrics.
        """
        metrics = self._result.metrics

        return {
            "cagr": f"{metrics.cagr:.2%}",
            "total_return": f"{metrics.total_return:.2%}",
            "sharpe_ratio": f"{metrics.sharpe_ratio:.2f}",
            "sortino_ratio": f"{metrics.sortino_ratio:.2f}",
            "maximum_drawdown": f"{metrics.maximum_drawdown:.2%}",
            "win_rate": f"{metrics.win_rate:.2%}",
            "profit_factor": f"{metrics.profit_factor:.2f}",
            "total_trades": metrics.number_of_trades,
            "expectancy": f"{metrics.expectancy:.2f}",
        }

    def full_report(self) -> dict[str, Any]:
        """Generate complete report.

        Returns:
            Dictionary with all report sections.
        """
        return {
            "strategy_name": self._result.strategy_name,
            "evaluated_at": self._result.evaluated_at.isoformat(),
            "config": {
                "initial_capital": self._result.config.initial_capital,
                "start_date": self._result.config.start_date.isoformat(),
                "end_date": self._result.config.end_date.isoformat(),
                "symbols": self._result.config.symbols,
            },
            "trade_summary": self.trade_summary(),
            "performance_summary": self.performance_summary(),
            "equity_curve": self.equity_curve_data(),
            "drawdown_curve": self.drawdown_curve_data(),
            "monthly_returns": self.monthly_returns_data(),
            "yearly_returns": self.yearly_returns_data(),
            "statistics": {
                "total_orders": self._result.statistics.total_orders,
                "filled_orders": self._result.statistics.filled_orders,
                "cancelled_orders": self._result.statistics.cancelled_orders,
                "rejected_orders": self._result.statistics.rejected_orders,
                "total_commission": f"{self._result.statistics.total_commission:.2f}",
                "total_slippage": f"{self._result.statistics.total_slippage:.2f}",
                "elapsed_seconds": f"{self._result.statistics.elapsed_seconds:.2f}",
            },
        }
