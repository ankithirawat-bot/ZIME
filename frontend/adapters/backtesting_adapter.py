"""Adapter bridging Backtesting workspace ViewModels with backend Backtesting Engine."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from frontend.viewmodels.backtesting_viewmodels import (
    BacktestConfiguration,
    BacktestResult,
    EquityPoint,
    PerformanceMetrics,
    Trade,
)


class BackendProtocol(Protocol):
    def query_pluggable_strategies(self) -> list[str]:
        ...

    def query_backtest(
        self,
        *,
        strategy_name: str,
        universe: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        initial_capital: float,
        commission: float,
        slippage: float,
    ) -> dict:
        ...



class BacktestingAdapter:
    """Adapter providing deterministic sample or live converted data to the UI."""

    def __init__(self, controller) -> None:
        self._controller = controller

    def available_strategies(self) -> list[str]:
        return ["Momentum", "MeanReversion", "TrendFollower", "RS", "Volatility", "Composite"]

    def sample_configuration(self) -> BacktestConfiguration:
        return BacktestConfiguration(
            strategy_name="CompSample",
            universe="NIFTY50",
            timeframe="D1",
            start_date="2020-01-01",
            end_date="2024-12-31",
            initial_capital=1_000_000.0,
            commission=0.001,
            slippage=0.001,
        )

    def sample_result(self) -> BacktestResult:
        cfg = self.sample_configuration()
        metrics = PerformanceMetrics(
            net_return=29.2,
            cagr=6.5,
            sharpe_ratio=0.76,
            max_drawdown=-19.2,
            win_rate=56.0,
            profit_factor=1.32,
            total_trades=125,
            expectancy=1.8,
        )
        trades = [
            Trade(
                trade_id=i,
                symbol="RELIANCE",
                entry_date="2023-01-03",
                exit_date="2023-01-10",
                direction="long",
                entry_price=2675.0,
                exit_price=2710.0,
                pnl=3500.0,
                return_pct=1.31,
            )
            for i in range(1, 6)
        ]
        equity = [(d, 1_000_000.0 * (1.0 + m / 100.0)) for d, m in [
            ("2020-01-01", 0.0),
            ("2020-06-30", 7.2),
            ("2021-06-30", 18.0),
            ("2022-06-30", 22.1),
            ("2023-06-30", 25.8),
            ("2024-12-31", 29.2),
        ]]
        curve = [EquityPoint(timestamp=t, cumulative_value=v) for t, v in equity]
        return BacktestResult(
            configuration=cfg,
            metrics=metrics,
            equity_curve=curve,
            trades=trades,
            completed_at_utc=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        )

    def load_backtest(
        self,
        config: BacktestConfiguration,
    ) -> BacktestResult | Exception | str:
        controller = self._controller
        try:
            res = controller.get_backtesting_engine().query_backtest(
                strategy_name=config.strategy_name,
                universe=config.universe,
                timeframe=config.timeframe,
                start_date=config.start_date,
                end_date=config.end_date,
                initial_capital=config.initial_capital,
                commission=config.commission,
                slippage=config.slippage,
            )
            metrics = PerformanceMetrics(
                net_return=float(res["net_return"]),
                cagr=float(res["cagr"]),
                sharpe_ratio=float(res["sharpe_ratio"]),
                max_drawdown=float(res["max_drawdown"]),
                win_rate=float(res["win_rate"]),
                profit_factor=float(res["profit_factor"]),
                total_trades=int(res["total_trades"]),
                expectancy=float(res["expectancy"]),
            )
            trades = [
                Trade(
                    trade_id=int(t["trade_id"]),
                    symbol=str(t["symbol"]),
                    entry_date=str(t["entry_date"]),
                    exit_date=str(t["exit_date"]),
                    direction=str(t["direction"]),
                    entry_price=float(t["entry_price"]),
                    exit_price=float(t["exit_price"]),
                    pnl=float(t["pnl"]),
                    return_pct=float(t["return_pct"]),
                )
                for t in res.get("trades", [])
            ]
            curve = [
                EquityPoint(
                    timestamp=str(e["timestamp"]),
                    cumulative_value=float(e["cumulative_value"]),
                )
                for e in res.get("equity_curve", [])
            ]
            result = BacktestResult(
                configuration=config,
                metrics=metrics,
                equity_curve=curve,
                trades=trades,
                completed_at_utc=str(res.get("completed_at", "")),
            )
            return result
        except Exception as exc:
            return exc
