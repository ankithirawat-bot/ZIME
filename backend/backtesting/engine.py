"""Backtesting engine.

Core backtesting engine for replaying historical data and evaluating strategies.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from backend.backtesting.broker import Broker
from backend.backtesting.exceptions import (
    EmptyUniverseError,
    InsufficientDataError,
    InvalidBacktestConfigError,
)
from backend.backtesting.metrics import (
    calculate_drawdown_curve,
    calculate_monthly_returns,
    calculate_performance_metrics,
    calculate_yearly_returns,
)
from backend.backtesting.models import (
    BacktestConfig,
    BacktestDefinition,
    BacktestResult,
    BacktestStatistics,
    EquityPoint,
    Order,
    OrderStatus,
    PositionSide,
    Trade,
)
from backend.backtesting.portfolio import Portfolio


class BacktestEngine:
    """Core backtesting engine.

    Replays historical market data and evaluates strategies under realistic
    trading conditions.
    """

    def __init__(
        self,
        broker: Broker | None = None,
        portfolio: Portfolio | None = None,
    ) -> None:
        """Initialize the engine.

        Args:
            broker:    Broker for order execution.
            portfolio: Portfolio to manage.
        """
        self._broker = broker
        self._portfolio = portfolio

    def run(
        self,
        definition: BacktestDefinition,
        strategy_fn: Callable[[dict[str, Any]], str],
        historical_data: dict[str, list[dict[str, Any]]],
    ) -> BacktestResult:
        """Run a complete backtest.

        Args:
            definition:      Backtest definition.
            strategy_fn:     Strategy function that returns "BUY", "SELL", or "HOLD".
            historical_data: Historical data by symbol.

        Returns:
            BacktestResult with all results.

        Raises:
            EmptyUniverseError:     If no symbols provided.
            InsufficientDataError:  If insufficient historical data.
            InvalidBacktestConfigError: If config is invalid.
        """
        start_time = time.time()

        config = definition.config

        if not config.symbols:
            raise EmptyUniverseError()

        self._validate_config(config)

        broker = self._broker or Broker(config)
        portfolio = self._portfolio or Portfolio(config, broker)

        equity_curve: list[EquityPoint] = []
        trades: list[Trade] = []
        all_orders: list[Order] = []
        filled_count = 0
        cancelled_count = 0
        rejected_count = 0
        total_commission = 0.0
        total_slippage = 0.0

        dates = self._get_sorted_dates(historical_data, config)

        if not dates:
            raise InsufficientDataError("No historical data provided")

        for date in dates:
            current_prices = self._get_prices_at_date(historical_data, date, config.symbols)
            portfolio.set_market_prices(current_prices)

            market_data = self._build_market_data(historical_data, date, config.symbols)
            signal = strategy_fn(market_data)

            if signal == "BUY":
                orders = self._generate_buy_orders(
                    portfolio, current_prices, config.symbols
                )
            elif signal == "SELL":
                orders = self._generate_sell_orders(portfolio, current_prices)
            else:
                orders = []

            for order in orders:
                executed = broker.execute_order(
                    order,
                    current_prices.get(order.symbol, order.price),
                    portfolio.cash,
                    portfolio.holdings,
                )
                all_orders.append(executed)

                if executed.status == OrderStatus.FILLED:
                    filled_count += 1
                    costs = broker.calculate_transaction_cost(
                        executed.quantity, executed.filled_price
                    )
                    total_commission += costs["total"] - costs["slippage"]
                    total_slippage += costs["slippage"]

                    if executed.side == PositionSide.LONG:
                        if executed.order_id.startswith("BUY"):
                            portfolio.buy(
                                executed.symbol,
                                executed.quantity,
                                executed.filled_price,
                                current_prices,
                            )
                        else:
                            portfolio.sell(
                                executed.symbol,
                                executed.quantity,
                                executed.filled_price,
                                current_prices,
                            )
                            trade = self._create_trade(executed, current_prices)
                            if trade:
                                trades.append(trade)
                elif executed.status == OrderStatus.CANCELLED:
                    cancelled_count += 1
                elif executed.status == OrderStatus.REJECTED:
                    rejected_count += 1

            equity_point = EquityPoint(
                date=datetime.combine(date, datetime.min.time()),
                equity=portfolio.total_equity,
                cash=portfolio.cash,
            )
            equity_curve.append(equity_point)

        drawdown_curve = calculate_drawdown_curve(equity_curve)
        monthly_returns = calculate_monthly_returns(equity_curve)
        yearly_returns = calculate_yearly_returns(equity_curve)

        metrics = calculate_performance_metrics(
            equity_curve, trades, config, portfolio.exposure
        )

        elapsed = time.time() - start_time

        statistics = BacktestStatistics(
            total_orders=len(all_orders),
            filled_orders=filled_count,
            cancelled_orders=cancelled_count,
            rejected_orders=rejected_count,
            total_trades=len(trades),
            total_commission=total_commission,
            total_slippage=total_slippage,
            elapsed_seconds=elapsed,
            symbols_processed=config.symbols,
        )

        return BacktestResult(
            strategy_name=definition.metadata.name,
            config=config,
            trades=tuple(trades),
            equity_curve=tuple(equity_curve),
            drawdown_curve=tuple(
                EquityPoint(date=d, equity=e, cash=0.0)
                for d, e in drawdown_curve
            ),
            metrics=metrics,
            statistics=statistics,
            monthly_returns=tuple(monthly_returns),
            yearly_returns=tuple(yearly_returns),
        )

    def run_symbol(
        self,
        definition: BacktestDefinition,
        strategy_fn: Callable[[dict[str, Any]], str],
        historical_data: list[dict[str, Any]],
        symbol: str,
    ) -> BacktestResult:
        """Run a backtest for a single symbol.

        Args:
            definition:    Backtest definition.
            strategy_fn:   Strategy function.
            historical_data: Historical data for the symbol.
            symbol:        Symbol to backtest.

        Returns:
            BacktestResult with results.
        """
        return self.run(
            definition,
            strategy_fn,
            {symbol: historical_data},
        )

    def run_universe(
        self,
        definition: BacktestDefinition,
        strategy_fn: Callable[[dict[str, Any]], str],
        historical_data: dict[str, list[dict[str, Any]]],
    ) -> BacktestResult:
        """Run a backtest for multiple symbols.

        Args:
            definition:    Backtest definition.
            strategy_fn:   Strategy function.
            historical_data: Historical data by symbol.

        Returns:
            BacktestResult with results.
        """
        return self.run(definition, strategy_fn, historical_data)

    def _validate_config(self, config: BacktestConfig) -> None:
        """Validate backtest configuration.

        Args:
            config: Configuration to validate.

        Raises:
            InvalidBacktestConfigError: If config is invalid.
        """
        if config.initial_capital <= 0:
            raise InvalidBacktestConfigError(
                f"Initial capital must be positive, got {config.initial_capital}"
            )
        if config.start_date > config.end_date:
            raise InvalidBacktestConfigError(
                f"Start date {config.start_date} is after end date {config.end_date}"
            )

    def _get_sorted_dates(
        self,
        historical_data: dict[str, list[dict[str, Any]]],
        config: BacktestConfig,
    ) -> list[Any]:
        """Get sorted unique dates from historical data.

        Args:
            historical_data: Historical data by symbol.
            config:          Backtest configuration.

        Returns:
            Sorted list of dates.
        """
        all_dates = set()
        for symbol in config.symbols:
            if symbol in historical_data:
                for candle in historical_data[symbol]:
                    if "date" in candle:
                        all_dates.add(candle["date"])
                    elif "timestamp" in candle:
                        all_dates.add(candle["timestamp"])

        return sorted(all_dates)

    def _get_prices_at_date(
        self,
        historical_data: dict[str, list[dict[str, Any]]],
        date: Any,
        symbols: tuple[str, ...],
    ) -> dict[str, float]:
        """Get prices at a specific date.

        Args:
            historical_data: Historical data by symbol.
            date:           Target date.
            symbols:        Symbols to get prices for.

        Returns:
            Dictionary of symbol -> price.
        """
        prices = {}
        for symbol in symbols:
            if symbol in historical_data:
                for candle in historical_data[symbol]:
                    candle_date = candle.get("date") or candle.get("timestamp")
                    if candle_date == date:
                        prices[symbol] = candle.get("close", 0.0)
                        break
        return prices

    def _build_market_data(
        self,
        historical_data: dict[str, list[dict[str, Any]]],
        date: Any,
        symbols: tuple[str, ...],
    ) -> dict[str, Any]:
        """Build market data dictionary for strategy evaluation.

        Args:
            historical_data: Historical data by symbol.
            date:           Target date.
            symbols:        Symbols to include.

        Returns:
            Market data dictionary.
        """
        market_data = {"date": date, "symbols": {}}

        for symbol in symbols:
            if symbol in historical_data:
                for i, candle in enumerate(historical_data[symbol]):
                    candle_date = candle.get("date") or candle.get("timestamp")
                    if candle_date == date:
                        market_data["symbols"][symbol] = candle
                        if i > 0:
                            market_data["symbols"][f"{symbol}_prev"] = (
                                historical_data[symbol][i - 1]
                            )
                        break

        return market_data

    def _generate_buy_orders(
        self,
        portfolio: Portfolio,
        current_prices: dict[str, float],
        symbols: tuple[str, ...],
    ) -> list[Order]:
        """Generate buy orders.

        Args:
            portfolio:      Portfolio to check.
            current_prices: Current prices.
            symbols:        Symbols to consider.

        Returns:
            List of buy orders.
        """
        orders = []
        available_cash = portfolio.cash

        for symbol in symbols:
            if symbol not in current_prices or current_prices[symbol] <= 0:
                continue

            price = current_prices[symbol]
            if symbol in portfolio.holdings:
                continue

            max_shares = int(available_cash / (price * 1.01))
            if max_shares > 0:
                order = Order(
                    order_id=f"BUY_{symbol}_{datetime.now().astimezone().timestamp()}",
                    symbol=symbol,
                    side=PositionSide.LONG,
                    quantity=max_shares,
                    price=price,
                )
                orders.append(order)
                available_cash -= max_shares * price * 1.01

        return orders

    def _generate_sell_orders(
        self,
        portfolio: Portfolio,
        current_prices: dict[str, float],
    ) -> list[Order]:
        """Generate sell orders.

        Args:
            portfolio:      Portfolio to check.
            current_prices: Current prices.

        Returns:
            List of sell orders.
        """
        orders = []

        for symbol, quantity in portfolio.holdings.items():
            if quantity <= 0:
                continue

            price = current_prices.get(symbol, 0.0)
            if price <= 0:
                continue

            order = Order(
                order_id=f"SELL_{symbol}_{datetime.now().astimezone().timestamp()}",
                symbol=symbol,
                side=PositionSide.LONG,
                quantity=quantity,
                price=price,
            )
            orders.append(order)

        return orders

    def _create_trade(
        self,
        order: Order,
        current_prices: dict[str, float],
    ) -> Trade | None:
        """Create a trade record from a filled order.

        Args:
            order:          Filled order.
            current_prices: Current prices.

        Returns:
            Trade record or None.
        """
        if order.status != OrderStatus.FILLED:
            return None

        return Trade(
            trade_id=f"TRADE_{order.order_id}",
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            entry_price=order.filled_price,
            exit_price=order.filled_price,
            entry_date=order.filled_at or datetime.now().astimezone(),
            exit_date=order.filled_at or datetime.now().astimezone(),
            pnl=0.0,
            pnl_pct=0.0,
            commission=0.0,
            slippage=0.0,
            holding_period=0,
        )
