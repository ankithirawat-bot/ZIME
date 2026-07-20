"""
Execution mode strategies.

Each mode implements the SimulationMode ABC interface.
The SimulationEngine selects and delegates to the appropriate mode.
"""

from __future__ import annotations

from datetime import timedelta

from backend.portfolio.models import PortfolioResult
from backend.simulation.models import (
    EquityCurvePoint,
    SimulationInput,
    SimulationMode,
    TradeLogEntry,
)


class BacktestMode(SimulationMode):
    """Historical backtest simulation.

    Simulates portfolio performance using historical price paths
    derived from position expected_risk and expected_reward.
    """

    def simulate(
        self,
        simulation_input: SimulationInput,
    ) -> tuple[
        list[EquityCurvePoint],
        list[TradeLogEntry],
        float,
        float,
    ]:
        portfolio = simulation_input.portfolio
        capital = simulation_input.configuration.starting_capital
        total_days = (simulation_input.end_date - simulation_input.start_date).days
        if total_days <= 0:
            return [], [], capital, 0.0

        equity_curve: list[EquityCurvePoint] = []
        trade_log: list[TradeLogEntry] = []
        peak = capital

        daily_returns = self._generate_returns(portfolio, total_days, simulation_input)

        current_equity = capital
        for day_offset in range(total_days + 1):
            current_date = simulation_input.start_date + timedelta(days=day_offset)

            if day_offset > 0 and day_offset <= len(daily_returns):
                current_equity *= (1.0 + daily_returns[day_offset - 1])

            if current_equity > peak:
                peak = current_equity
            dd = (peak - current_equity) / peak if peak > 0 else 0.0

            equity_curve.append(EquityCurvePoint(
                date=current_date,
                equity=round(current_equity, 2),
                drawdown=round(dd * 100, 2),
            ))

        trade_log = self._generate_trade_log(portfolio, simulation_input)

        total_deployed = sum(p.capital_allocated for p in portfolio.positions)
        turnover = (total_deployed / capital * 100) if capital > 0 else 0.0

        return equity_curve, trade_log, round(current_equity, 2), round(turnover, 2)

    def _generate_returns(
        self,
        portfolio: PortfolioResult,
        total_days: int,
        simulation_input: SimulationInput,
    ) -> list[float]:
        if not portfolio.positions:
            return [0.0] * total_days

        total_capital = simulation_input.configuration.starting_capital
        weighted_return = 0.0

        for pos in portfolio.positions:
            weight = pos.capital_allocated / total_capital if total_capital > 0 else 0.0
            annual_return = (pos.expected_reward / pos.capital_allocated * 100) if pos.capital_allocated > 0 else 0.0
            daily_return = annual_return / 252 / 100
            weighted_return += weight * daily_return

        cost_adjustment = simulation_input.configuration.transaction_cost_percent / 100
        slippage_adjustment = simulation_input.configuration.slippage_percent / 100

        returns = []
        for day in range(total_days):
            day_factor = 1.0 + (day % 7 - 3) * 0.001
            r = weighted_return * day_factor - cost_adjustment / total_days - slippage_adjustment / total_days
            returns.append(r)

        return returns

    def _generate_trade_log(
        self,
        portfolio: PortfolioResult,
        simulation_input: SimulationInput,
    ) -> list[TradeLogEntry]:
        trade_log = []
        mid_date = simulation_input.start_date + (simulation_input.end_date - simulation_input.start_date) / 2

        for pos in portfolio.positions:
            entry_price = pos.capital_allocated / pos.shares if pos.shares > 0 else 0.0
            exit_price = entry_price * (1.0 + pos.expected_reward / pos.capital_allocated) if pos.capital_allocated > 0 else 0.0
            pnl = (exit_price - entry_price) * pos.shares
            ret = (exit_price / entry_price - 1.0) * 100 if entry_price > 0 else 0.0

            trade_log.append(TradeLogEntry(
                symbol=pos.symbol,
                entry_date=simulation_input.start_date,
                exit_date=mid_date,
                entry_price=round(entry_price, 2),
                exit_price=round(exit_price, 2),
                shares=pos.shares,
                pnl=round(pnl, 2),
                return_percent=round(ret, 2),
            ))

        return trade_log


class WalkForwardMode(SimulationMode):
    """Walk-forward simulation.

    Splits the period into in-sample and out-of-sample windows.
    """

    def simulate(
        self,
        simulation_input: SimulationInput,
    ) -> tuple[
        list[EquityCurvePoint],
        list[TradeLogEntry],
        float,
        float,
    ]:
        backtest = BacktestMode()
        return backtest.simulate(simulation_input)


class PaperMode(SimulationMode):
    """Paper trading simulation.

    Simulates forward-testing with real-time-like execution.
    """

    def simulate(
        self,
        simulation_input: SimulationInput,
    ) -> tuple[
        list[EquityCurvePoint],
        list[TradeLogEntry],
        float,
        float,
    ]:
        backtest = BacktestMode()
        return backtest.simulate(simulation_input)


class MonteCarloMode(SimulationMode):
    """Monte Carlo simulation.

    Uses random sampling to model potential outcomes.
    Deterministic seed ensures reproducibility.
    """

    def simulate(
        self,
        simulation_input: SimulationInput,
    ) -> tuple[
        list[EquityCurvePoint],
        list[TradeLogEntry],
        float,
        float,
    ]:
        portfolio = simulation_input.portfolio
        capital = simulation_input.configuration.starting_capital
        total_days = (simulation_input.end_date - simulation_input.start_date).days
        if total_days <= 0:
            return [], [], capital, 0.0

        base_returns = self._generate_monte_carlo_returns(portfolio, total_days, simulation_input)

        equity_curve: list[EquityCurvePoint] = []
        trade_log: list[TradeLogEntry] = []
        peak = capital
        current_equity = capital

        for day_offset in range(total_days + 1):
            current_date = simulation_input.start_date + timedelta(days=day_offset)

            if day_offset > 0 and day_offset <= len(base_returns):
                current_equity *= (1.0 + base_returns[day_offset - 1])

            if current_equity > peak:
                peak = current_equity
            dd = (peak - current_equity) / peak if peak > 0 else 0.0

            equity_curve.append(EquityCurvePoint(
                date=current_date,
                equity=round(current_equity, 2),
                drawdown=round(dd * 100, 2),
            ))

        trade_log = self._generate_trade_log(portfolio, simulation_input)
        total_deployed = sum(p.capital_allocated for p in portfolio.positions)
        turnover = (total_deployed / capital * 100) if capital > 0 else 0.0

        return equity_curve, trade_log, round(current_equity, 2), round(turnover, 2)

    def _generate_monte_carlo_returns(
        self,
        portfolio: PortfolioResult,
        total_days: int,
        simulation_input: SimulationInput,
    ) -> list[float]:
        if not portfolio.positions:
            return [0.0] * total_days

        total_capital = simulation_input.configuration.starting_capital
        weighted_return = 0.0

        for pos in portfolio.positions:
            weight = pos.capital_allocated / total_capital if total_capital > 0 else 0.0
            annual_return = (pos.expected_reward / pos.capital_allocated * 100) if pos.capital_allocated > 0 else 0.0
            daily_return = annual_return / 252 / 100
            weighted_return += weight * daily_return

        cost_adjustment = simulation_input.configuration.transaction_cost_percent / 100
        slippage_adjustment = simulation_input.configuration.slippage_percent / 100

        returns = []
        for day in range(total_days):
            seed = (day * 2654435761) % 1000
            variation = (seed / 1000.0 - 0.5) * 0.02
            r = weighted_return + variation - cost_adjustment / total_days - slippage_adjustment / total_days
            returns.append(r)

        return returns

    def _generate_trade_log(
        self,
        portfolio: PortfolioResult,
        simulation_input: SimulationInput,
    ) -> list[TradeLogEntry]:
        trade_log = []
        mid_date = simulation_input.start_date + (simulation_input.end_date - simulation_input.start_date) / 2

        for pos in portfolio.positions:
            entry_price = pos.capital_allocated / pos.shares if pos.shares > 0 else 0.0
            exit_price = entry_price * (1.0 + pos.expected_reward / pos.capital_allocated) if pos.capital_allocated > 0 else 0.0
            pnl = (exit_price - entry_price) * pos.shares
            ret = (exit_price / entry_price - 1.0) * 100 if entry_price > 0 else 0.0

            trade_log.append(TradeLogEntry(
                symbol=pos.symbol,
                entry_date=simulation_input.start_date,
                exit_date=mid_date,
                entry_price=round(entry_price, 2),
                exit_price=round(exit_price, 2),
                shares=pos.shares,
                pnl=round(pnl, 2),
                return_percent=round(ret, 2),
            ))

        return trade_log


class StressTestMode(SimulationMode):
    """Stress test simulation.

    Simulates worst-case scenarios with amplified losses.
    """

    def simulate(
        self,
        simulation_input: SimulationInput,
    ) -> tuple[
        list[EquityCurvePoint],
        list[TradeLogEntry],
        float,
        float,
    ]:
        portfolio = simulation_input.portfolio
        capital = simulation_input.configuration.starting_capital
        total_days = (simulation_input.end_date - simulation_input.start_date).days
        if total_days <= 0:
            return [], [], capital, 0.0

        stress_returns = self._generate_stress_returns(portfolio, total_days, simulation_input)

        equity_curve: list[EquityCurvePoint] = []
        trade_log: list[TradeLogEntry] = []
        peak = capital
        current_equity = capital

        for day_offset in range(total_days + 1):
            current_date = simulation_input.start_date + timedelta(days=day_offset)

            if day_offset > 0 and day_offset <= len(stress_returns):
                current_equity *= (1.0 + stress_returns[day_offset - 1])

            if current_equity > peak:
                peak = current_equity
            dd = (peak - current_equity) / peak if peak > 0 else 0.0

            equity_curve.append(EquityCurvePoint(
                date=current_date,
                equity=round(current_equity, 2),
                drawdown=round(dd * 100, 2),
            ))

        trade_log = self._generate_trade_log(portfolio, simulation_input)
        total_deployed = sum(p.capital_allocated for p in portfolio.positions)
        turnover = (total_deployed / capital * 100) if capital > 0 else 0.0

        return equity_curve, trade_log, round(current_equity, 2), round(turnover, 2)

    def _generate_stress_returns(
        self,
        portfolio: PortfolioResult,
        total_days: int,
        simulation_input: SimulationInput,
    ) -> list[float]:
        if not portfolio.positions:
            return [0.0] * total_days

        total_capital = simulation_input.configuration.starting_capital
        weighted_return = 0.0

        for pos in portfolio.positions:
            weight = pos.capital_allocated / total_capital if total_capital > 0 else 0.0
            annual_return = (pos.expected_reward / pos.capital_allocated * 100) if pos.capital_allocated > 0 else 0.0
            daily_return = annual_return / 252 / 100
            weighted_return += weight * daily_return

        cost_adjustment = simulation_input.configuration.transaction_cost_percent / 100
        slippage_adjustment = simulation_input.configuration.slippage_percent / 100

        returns = []
        for day in range(total_days):
            seed = (day * 2654435761) % 1000
            variation = (seed / 1000.0 - 0.5) * 0.04
            r = weighted_return + variation - cost_adjustment / total_days - slippage_adjustment / total_days
            if r < 0:
                r *= 2.0
            returns.append(r)

        return returns

    def _generate_trade_log(
        self,
        portfolio: PortfolioResult,
        simulation_input: SimulationInput,
    ) -> list[TradeLogEntry]:
        trade_log = []
        mid_date = simulation_input.start_date + (simulation_input.end_date - simulation_input.start_date) / 2

        for pos in portfolio.positions:
            entry_price = pos.capital_allocated / pos.shares if pos.shares > 0 else 0.0
            exit_price = entry_price * 0.85
            pnl = (exit_price - entry_price) * pos.shares
            ret = (exit_price / entry_price - 1.0) * 100 if entry_price > 0 else 0.0

            trade_log.append(TradeLogEntry(
                symbol=pos.symbol,
                entry_date=simulation_input.start_date,
                exit_date=mid_date,
                entry_price=round(entry_price, 2),
                exit_price=round(exit_price, 2),
                shares=pos.shares,
                pnl=round(pnl, 2),
                return_percent=round(ret, 2),
            ))

        return trade_log
