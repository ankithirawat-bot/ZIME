"""Backtesting engine tests.

Covers all functionality including order execution, portfolio management,
performance metrics, and reporting.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from backend.backtesting.broker import Broker
from backend.backtesting.engine import BacktestEngine
from backend.backtesting.exceptions import (
    BacktestError,
    EmptyUniverseError,
    InsufficientCashError,
    InsufficientDataError,
    InsufficientSharesError,
    InvalidBacktestConfigError,
    InvalidOrderError,
    OrderExecutionError,
    PositionNotFoundError,
    StrategyError,
)
from backend.backtesting.factory import BacktestFactory
from backend.backtesting.metrics import (
    calculate_annualized_return,
    calculate_cagr,
    calculate_calmar_ratio,
    calculate_drawdown_curve,
    calculate_maximum_drawdown,
    calculate_monthly_returns,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_total_return,
    calculate_trade_metrics,
    calculate_yearly_returns,
)
from backend.backtesting.models import (
    BacktestConfig,
    BacktestDefinition,
    BacktestMetadata,
    BacktestResult,
    BacktestStatistics,
    DrawdownPoint,
    EquityPoint,
    Order,
    OrderStatus,
    OrderType,
    PerformanceMetrics,
    PortfolioSnapshot,
    Position,
    PositionSide,
    Trade,
)
from backend.backtesting.portfolio import Portfolio
from backend.backtesting.report import BacktestReport


def _create_config(**kwargs: object) -> BacktestConfig:
    """Create a test configuration."""
    defaults = {
        "initial_capital": 1_000_000.0,
        "start_date": date(2023, 1, 1),
        "end_date": date(2023, 12, 31),
        "symbols": ("RELIANCE", "TCS", "INFY"),
    }
    defaults.update(kwargs)
    return BacktestConfig(**defaults)  # type: ignore[arg-type]


def _create_historical_data(
    symbol: str = "RELIANCE",
    start_date: date = date(2023, 1, 1),
    days: int = 10,
    base_price: float = 2000.0,
    daily_return: float = 0.01,
) -> list[dict[str, object]]:
    """Create test historical data."""
    data = []
    price = base_price
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        open_price = price * (1 + (daily_return * 0.5))
        close_price = price * (1 + daily_return)
        high = max(open_price, close_price) * 1.005
        low = min(open_price, close_price) * 0.995
        data.append({
            "date": current_date,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close_price,
            "volume": 1000000,
        })
        price = close_price
    return data


def _create_multi_symbol_data(
    symbols: tuple[str, ...] = ("RELIANCE", "TCS", "INFY"),
    start_date: date = date(2023, 1, 1),
    days: int = 10,
) -> dict[str, list[dict[str, object]]]:
    """Create test data for multiple symbols."""
    data = {}
    for i, symbol in enumerate(symbols):
        base_price = 2000.0 + (i * 500)
        data[symbol] = _create_historical_data(
            symbol, start_date, days, base_price, 0.01
        )
    return data


def _create_result(
    trades: tuple[Trade, ...] = (),
    equity_curve: tuple[EquityPoint, ...] = (),
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """Create a test result."""
    return BacktestResult(
        strategy_name="TestStrategy",
        config=config or _create_config(),
        trades=trades,
        equity_curve=equity_curve,
    )


class TestSignals:
    """Test signal types and scores."""

    def test_order_types(self) -> None:
        assert OrderType.MARKET == "MARKET"
        assert OrderType.LIMIT == "LIMIT"
        assert OrderType.STOP == "STOP"

    def test_order_status(self) -> None:
        assert OrderStatus.PENDING == "PENDING"
        assert OrderStatus.FILLED == "FILLED"
        assert OrderStatus.CANCELLED == "CANCELLED"
        assert OrderStatus.EXPIRED == "EXPIRED"
        assert OrderStatus.REJECTED == "REJECTED"

    def test_position_side(self) -> None:
        assert PositionSide.LONG == "LONG"
        assert PositionSide.SHORT == "SHORT"


class TestBroker:
    """Test broker execution."""

    def test_broker_initialization(self) -> None:
        config = _create_config()
        broker = Broker(config)
        assert broker.config == config

    def test_execute_market_order_buy(self) -> None:
        config = _create_config()
        broker = Broker(config)
        order = Order(
            order_id="BUY_1",
            symbol="RELIANCE",
            order_type=OrderType.MARKET,
            side=PositionSide.LONG,
            quantity=10,
            price=2000.0,
        )
        result = broker.execute_order(order, 2000.0, 1_000_000.0, {})
        assert result.status == OrderStatus.FILLED
        assert result.filled_price == 2000.0

    def test_execute_market_order_sell(self) -> None:
        config = _create_config()
        broker = Broker(config)
        order = Order(
            order_id="SELL_1",
            symbol="RELIANCE",
            order_type=OrderType.MARKET,
            side=PositionSide.LONG,
            quantity=10,
            price=2000.0,
        )
        result = broker.execute_order(order, 2000.0, 1_000_000.0, {"RELIANCE": 10})
        assert result.status == OrderStatus.FILLED
        assert result.filled_price == 2000.0

    def test_execute_limit_order_fills(self) -> None:
        config = _create_config()
        broker = Broker(config)
        order = Order(
            order_id="LIMIT_1",
            symbol="RELIANCE",
            order_type=OrderType.LIMIT,
            side=PositionSide.LONG,
            quantity=10,
            price=2100.0,
        )
        result = broker.execute_order(order, 2050.0, 1_000_000.0, {})
        assert result.status == OrderStatus.FILLED
        assert result.filled_price == 2100.0

    def test_execute_limit_order_pending(self) -> None:
        config = _create_config()
        broker = Broker(config)
        order = Order(
            order_id="LIMIT_2",
            symbol="RELIANCE",
            order_type=OrderType.LIMIT,
            side=PositionSide.LONG,
            quantity=10,
            price=1900.0,
        )
        result = broker.execute_order(order, 2000.0, 1_000_000.0, {})
        assert result.status == OrderStatus.PENDING

    def test_execute_stop_order_fills(self) -> None:
        config = _create_config()
        broker = Broker(config)
        order = Order(
            order_id="STOP_1",
            symbol="RELIANCE",
            order_type=OrderType.STOP,
            side=PositionSide.LONG,
            quantity=10,
            price=2000.0,
            stop_price=1900.0,
        )
        result = broker.execute_order(order, 1950.0, 1_000_000.0, {})
        assert result.status == OrderStatus.FILLED

    def test_execute_stop_order_pending(self) -> None:
        config = _create_config()
        broker = Broker(config)
        order = Order(
            order_id="STOP_2",
            symbol="RELIANCE",
            order_type=OrderType.STOP,
            side=PositionSide.LONG,
            quantity=10,
            price=2000.0,
            stop_price=2100.0,
        )
        result = broker.execute_order(order, 2050.0, 1_000_000.0, {})
        assert result.status == OrderStatus.PENDING

    def test_cancel_order(self) -> None:
        config = _create_config()
        broker = Broker(config)
        order = Order(
            order_id="CANCEL_1",
            symbol="RELIANCE",
            order_type=OrderType.MARKET,
            side=PositionSide.LONG,
            quantity=10,
            price=2000.0,
        )
        result = broker.cancel_order(order)
        assert result.status == OrderStatus.CANCELLED

    def test_cancel_filled_order_raises(self) -> None:
        config = _create_config()
        broker = Broker(config)
        order = Order(
            order_id="FILLED_1",
            symbol="RELIANCE",
            order_type=OrderType.MARKET,
            side=PositionSide.LONG,
            quantity=10,
            price=2000.0,
            status=OrderStatus.FILLED,
        )
        with pytest.raises(OrderExecutionError):
            broker.cancel_order(order)

    def test_calculate_transaction_cost(self) -> None:
        config = _create_config()
        broker = Broker(config)
        costs = broker.calculate_transaction_cost(100, 2000.0)
        assert costs["brokerage"] > 0
        assert costs["stt"] > 0
        assert costs["exchange"] > 0
        assert costs["sebi"] > 0
        assert costs["gst"] > 0
        assert costs["stamp_duty"] > 0
        assert costs["slippage"] > 0
        assert costs["total"] > 0

    def test_invalid_quantity_raises(self) -> None:
        config = _create_config()
        broker = Broker(config)
        order = Order(
            order_id="INVALID_1",
            symbol="RELIANCE",
            order_type=OrderType.MARKET,
            side=PositionSide.LONG,
            quantity=0,
            price=2000.0,
        )
        with pytest.raises(InvalidOrderError):
            broker.execute_order(order, 2000.0, 1_000_000.0, {})

    def test_invalid_price_raises(self) -> None:
        config = _create_config()
        broker = Broker(config)
        order = Order(
            order_id="INVALID_2",
            symbol="RELIANCE",
            order_type=OrderType.MARKET,
            side=PositionSide.LONG,
            quantity=10,
            price=2000.0,
        )
        with pytest.raises(InvalidOrderError):
            broker.execute_order(order, -100.0, 1_000_000.0, {})


class TestPortfolio:
    """Test portfolio management."""

    def test_portfolio_initialization(self) -> None:
        config = _create_config()
        portfolio = Portfolio(config)
        assert portfolio.cash == 1_000_000.0
        assert portfolio.holdings == {}
        assert portfolio.total_equity == 1_000_000.0

    def test_buy_shares(self) -> None:
        config = _create_config()
        portfolio = Portfolio(config)
        order = portfolio.buy("RELIANCE", 10, 2000.0)
        assert order.status == OrderStatus.FILLED
        assert portfolio.holdings["RELIANCE"] == 10
        assert portfolio.cash < 1_000_000.0

    def test_sell_shares(self) -> None:
        config = _create_config()
        portfolio = Portfolio(config)
        portfolio.buy("RELIANCE", 10, 2000.0)
        order = portfolio.sell("RELIANCE", 5, 2100.0)
        assert order.status == OrderStatus.FILLED
        assert portfolio.holdings["RELIANCE"] == 5

    def test_sell_all_shares(self) -> None:
        config = _create_config()
        portfolio = Portfolio(config)
        portfolio.buy("RELIANCE", 10, 2000.0)
        order = portfolio.sell("RELIANCE", 10, 2100.0)
        assert order.status == OrderStatus.FILLED
        assert "RELIANCE" not in portfolio.holdings or portfolio.holdings.get("RELIANCE", 0) == 0

    def test_sell_insufficient_shares_raises(self) -> None:
        config = _create_config()
        portfolio = Portfolio(config)
        with pytest.raises(InsufficientSharesError):
            portfolio.sell("RELIANCE", 10, 2000.0)

    def test_update_market_value(self) -> None:
        config = _create_config()
        portfolio = Portfolio(config)
        portfolio.buy("RELIANCE", 10, 2000.0)
        portfolio.update_market_value("RELIANCE", 2100.0)
        assert portfolio.unrealized_pnl > 0

    def test_close_position(self) -> None:
        config = _create_config()
        portfolio = Portfolio(config)
        portfolio.buy("RELIANCE", 10, 2000.0)
        order = portfolio.close_position("RELIANCE", 2100.0)
        assert order is not None
        assert order.status == OrderStatus.FILLED

    def test_close_nonexistent_position(self) -> None:
        config = _create_config()
        portfolio = Portfolio(config)
        order = portfolio.close_position("RELIANCE", 2000.0)
        assert order is None

    def test_get_positions(self) -> None:
        config = _create_config()
        portfolio = Portfolio(config)
        portfolio.buy("RELIANCE", 10, 2000.0)
        positions = portfolio.get_positions({"RELIANCE": 2100.0})
        assert len(positions) == 1
        assert positions[0].symbol == "RELIANCE"
        assert positions[0].quantity == 10

    def test_get_snapshot(self) -> None:
        config = _create_config()
        portfolio = Portfolio(config)
        portfolio.buy("RELIANCE", 10, 2000.0)
        snapshot = portfolio.get_snapshot(market_prices={"RELIANCE": 2100.0})
        assert isinstance(snapshot, PortfolioSnapshot)
        assert snapshot.cash < 1_000_000.0
        assert snapshot.holdings_value > 0

    def test_total_equity(self) -> None:
        config = _create_config()
        portfolio = Portfolio(config)
        initial_equity = portfolio.total_equity
        portfolio.buy("RELIANCE", 10, 2000.0)
        assert portfolio.total_equity < initial_equity

    def test_exposure(self) -> None:
        config = _create_config()
        portfolio = Portfolio(config)
        assert portfolio.exposure == 0.0
        portfolio.buy("RELIANCE", 10, 2000.0)
        assert portfolio.exposure > 0


class TestMetrics:
    """Test performance metrics calculations."""

    def test_calculate_cagr(self) -> None:
        cagr = calculate_cagr(1000, 2000, 2)
        assert cagr == pytest.approx(0.4142, abs=0.01)

    def test_calculate_cagr_zero_years(self) -> None:
        cagr = calculate_cagr(1000, 2000, 0)
        assert cagr == 0.0

    def test_calculate_total_return(self) -> None:
        ret = calculate_total_return(1000, 1500)
        assert ret == pytest.approx(0.5)

    def test_calculate_total_return_zero(self) -> None:
        ret = calculate_total_return(0, 1500)
        assert ret == 0.0

    def test_calculate_annualized_return(self) -> None:
        ann = calculate_annualized_return(0.5, 2)
        assert ann == pytest.approx(0.2247, abs=0.01)

    def test_calculate_sharpe_ratio(self) -> None:
        returns = [0.01, 0.02, -0.01, 0.015, 0.005]
        sharpe = calculate_sharpe_ratio(returns, 0.06)
        assert isinstance(sharpe, float)

    def test_calculate_sharpe_ratio_empty(self) -> None:
        sharpe = calculate_sharpe_ratio([], 0.06)
        assert sharpe == 0.0

    def test_calculate_sortino_ratio(self) -> None:
        returns = [0.01, 0.02, -0.01, 0.015, 0.005]
        sortino = calculate_sortino_ratio(returns, 0.06)
        assert isinstance(sortino, float)

    def test_calculate_sortino_ratio_no_downside(self) -> None:
        returns = [0.01, 0.02, 0.015, 0.005]
        sortino = calculate_sortino_ratio(returns, 0.06)
        assert sortino == 0.0

    def test_calculate_calmar_ratio(self) -> None:
        calmar = calculate_calmar_ratio(0.2, 0.1)
        assert calmar == pytest.approx(2.0)

    def test_calculate_calmar_ratio_zero_dd(self) -> None:
        calmar = calculate_calmar_ratio(0.2, 0.0)
        assert calmar == 0.0

    def test_calculate_maximum_drawdown(self) -> None:
        equity_curve = [
            EquityPoint(date=datetime(2023, 1, 1), equity=100000),
            EquityPoint(date=datetime(2023, 1, 2), equity=110000),
            EquityPoint(date=datetime(2023, 1, 3), equity=105000),
            EquityPoint(date=datetime(2023, 1, 4), equity=95000),
            EquityPoint(date=datetime(2023, 1, 5), equity=100000),
        ]
        max_dd = calculate_maximum_drawdown(equity_curve)
        assert max_dd == pytest.approx(0.1364, abs=0.01)

    def test_calculate_maximum_drawdown_empty(self) -> None:
        max_dd = calculate_maximum_drawdown([])
        assert max_dd == 0.0

    def test_calculate_drawdown_curve(self) -> None:
        equity_curve = [
            EquityPoint(date=datetime(2023, 1, 1), equity=100000),
            EquityPoint(date=datetime(2023, 1, 2), equity=110000),
            EquityPoint(date=datetime(2023, 1, 3), equity=105000),
        ]
        drawdowns = calculate_drawdown_curve(equity_curve)
        assert len(drawdowns) == 3
        assert drawdowns[0][1] == 0.0
        assert drawdowns[1][1] == 0.0
        assert drawdowns[2][1] < 0

    def test_calculate_trade_metrics(self) -> None:
        trades = [
            Trade(
                trade_id="T1",
                symbol="RELIANCE",
                pnl=1000,
                holding_period=5,
            ),
            Trade(
                trade_id="T2",
                symbol="TCS",
                pnl=-500,
                holding_period=3,
            ),
            Trade(
                trade_id="T3",
                symbol="INFY",
                pnl=2000,
                holding_period=10,
            ),
        ]
        metrics = calculate_trade_metrics(trades)
        assert metrics["win_rate"] == pytest.approx(2 / 3)
        assert metrics["loss_rate"] == pytest.approx(1 / 3)
        assert metrics["profit_factor"] > 0
        assert metrics["average_holding"] == pytest.approx(6.0)

    def test_calculate_trade_metrics_empty(self) -> None:
        metrics = calculate_trade_metrics([])
        assert metrics["win_rate"] == 0.0
        assert metrics["number_of_trades"] == 0

    def test_calculate_monthly_returns(self) -> None:
        equity_curve = [
            EquityPoint(date=datetime(2023, 1, 31), equity=100000),
            EquityPoint(date=datetime(2023, 2, 1), equity=105000),
            EquityPoint(date=datetime(2023, 2, 28), equity=110000),
        ]
        monthly = calculate_monthly_returns(equity_curve)
        assert len(monthly) > 0

    def test_calculate_yearly_returns(self) -> None:
        equity_curve = [
            EquityPoint(date=datetime(2023, 1, 1), equity=100000),
            EquityPoint(date=datetime(2023, 12, 31), equity=120000),
        ]
        yearly = calculate_yearly_returns(equity_curve)
        assert len(yearly) > 0
        assert yearly[0][1] == pytest.approx(0.2)


class TestReport:
    """Test report generation."""

    def test_trade_summary(self) -> None:
        trades = (
            Trade(trade_id="T1", symbol="RELIANCE", pnl=1000),
            Trade(trade_id="T2", symbol="TCS", pnl=-500),
        )
        result = _create_result(trades=trades)
        report = BacktestReport(result)
        summary = report.trade_summary()
        assert summary["total_trades"] == 2
        assert summary["winning_trades"] == 1
        assert summary["losing_trades"] == 1

    def test_trade_summary_empty(self) -> None:
        result = _create_result()
        report = BacktestReport(result)
        summary = report.trade_summary()
        assert summary["total_trades"] == 0

    def test_equity_curve_data(self) -> None:
        equity_curve = (
            EquityPoint(date=datetime(2023, 1, 1), equity=100000, cash=50000),
            EquityPoint(date=datetime(2023, 1, 2), equity=105000, cash=55000),
        )
        result = _create_result(equity_curve=equity_curve)
        report = BacktestReport(result)
        data = report.equity_curve_data()
        assert len(data) == 2
        assert data[0]["equity"] == 100000

    def test_performance_summary(self) -> None:
        result = _create_result()
        report = BacktestReport(result)
        summary = report.performance_summary()
        assert "cagr" in summary
        assert "sharpe_ratio" in summary

    def test_full_report(self) -> None:
        result = _create_result()
        report = BacktestReport(result)
        full = report.full_report()
        assert "strategy_name" in full
        assert "config" in full
        assert "trade_summary" in full
        assert "performance_summary" in full


class TestFactory:
    """Test factory creation."""

    def test_create_default(self) -> None:
        engine = BacktestFactory.create()
        assert isinstance(engine, BacktestEngine)

    def test_create_with_config(self) -> None:
        config = _create_config()
        engine = BacktestFactory.create(config=config)
        assert isinstance(engine, BacktestEngine)

    def test_create_from_config(self) -> None:
        config = _create_config()
        engine = BacktestFactory.create_from_config(config)
        assert isinstance(engine, BacktestEngine)


class TestEngine:
    """Test backtesting engine."""

    def test_engine_initialization(self) -> None:
        engine = BacktestEngine()
        assert isinstance(engine, BacktestEngine)

    def test_engine_with_broker(self) -> None:
        config = _create_config()
        broker = Broker(config)
        engine = BacktestEngine(broker=broker)
        assert engine._broker == broker

    def test_engine_with_portfolio(self) -> None:
        config = _create_config()
        broker = Broker(config)
        portfolio = Portfolio(config, broker)
        engine = BacktestEngine(portfolio=portfolio)
        assert engine._portfolio == portfolio

    def test_run_single_symbol(self) -> None:
        config = _create_config(symbols=("RELIANCE",))
        definition = BacktestDefinition(
            metadata=BacktestMetadata(name="TestStrategy"),
            config=config,
        )
        historical_data = _create_historical_data("RELIANCE", days=5)
        engine = BacktestFactory.create(config=config)

        def strategy(data: dict) -> str:
            return "HOLD"

        result = engine.run(definition, strategy, {"RELIANCE": historical_data})
        assert isinstance(result, BacktestResult)
        assert result.strategy_name == "TestStrategy"

    def test_run_multiple_symbols(self) -> None:
        config = _create_config()
        definition = BacktestDefinition(
            metadata=BacktestMetadata(name="MultiSymbol"),
            config=config,
        )
        historical_data = _create_multi_symbol_data()
        engine = BacktestFactory.create(config=config)

        def strategy(data: dict) -> str:
            return "HOLD"

        result = engine.run(definition, strategy, historical_data)
        assert isinstance(result, BacktestResult)
        assert len(result.equity_curve) > 0

    def test_run_empty_universe_raises(self) -> None:
        config = _create_config(symbols=())
        definition = BacktestDefinition(
            metadata=BacktestMetadata(name="Empty"),
            config=config,
        )
        engine = BacktestFactory.create(config=config)

        def strategy(data: dict) -> str:
            return "HOLD"

        with pytest.raises(EmptyUniverseError):
            engine.run(definition, strategy, {})

    def test_run_empty_data_raises(self) -> None:
        config = _create_config(symbols=("RELIANCE",))
        definition = BacktestDefinition(
            metadata=BacktestMetadata(name="NoData"),
            config=config,
        )
        engine = BacktestFactory.create(config=config)

        def strategy(data: dict) -> str:
            return "HOLD"

        with pytest.raises(InsufficientDataError):
            engine.run(definition, strategy, {"RELIANCE": []})

    def test_run_invalid_config_raises(self) -> None:
        config = BacktestConfig(
            initial_capital=-100,
            symbols=("RELIANCE",),
            start_date=date(2023, 12, 31),
            end_date=date(2023, 1, 1),
        )
        definition = BacktestDefinition(
            metadata=BacktestMetadata(name="Invalid"),
            config=config,
        )
        engine = BacktestFactory.create(config=config)

        def strategy(data: dict) -> str:
            return "HOLD"

        with pytest.raises(InvalidBacktestConfigError):
            engine.run(definition, strategy, {"RELIANCE": []})

    def test_run_with_buy_signal(self) -> None:
        config = _create_config(symbols=("RELIANCE",))
        definition = BacktestDefinition(
            metadata=BacktestMetadata(name="BuyStrategy"),
            config=config,
        )
        historical_data = _create_historical_data("RELIANCE", days=5)
        engine = BacktestFactory.create(config=config)

        def strategy(data: dict) -> str:
            return "BUY"

        result = engine.run(definition, strategy, {"RELIANCE": historical_data})
        assert result.statistics.total_orders > 0

    def test_run_with_sell_signal(self) -> None:
        config = _create_config(symbols=("RELIANCE",))
        definition = BacktestDefinition(
            metadata=BacktestMetadata(name="SellStrategy"),
            config=config,
        )
        historical_data = _create_historical_data("RELIANCE", days=5)
        engine = BacktestFactory.create(config=config)

        buy_executed = False

        def strategy(data: dict) -> str:
            nonlocal buy_executed
            if not buy_executed:
                buy_executed = True
                return "BUY"
            return "SELL"

        result = engine.run(definition, strategy, {"RELIANCE": historical_data})
        assert result.statistics.total_orders > 0

    def test_run_symbol(self) -> None:
        config = _create_config(symbols=("RELIANCE",))
        definition = BacktestDefinition(
            metadata=BacktestMetadata(name="SingleSymbol"),
            config=config,
        )
        historical_data = _create_historical_data("RELIANCE", days=5)
        engine = BacktestFactory.create(config=config)

        def strategy(data: dict) -> str:
            return "HOLD"

        result = engine.run_symbol(definition, strategy, historical_data, "RELIANCE")
        assert isinstance(result, BacktestResult)

    def test_run_universe(self) -> None:
        config = _create_config()
        definition = BacktestDefinition(
            metadata=BacktestMetadata(name="UniverseStrategy"),
            config=config,
        )
        historical_data = _create_multi_symbol_data()
        engine = BacktestFactory.create(config=config)

        def strategy(data: dict) -> str:
            return "HOLD"

        result = engine.run_universe(definition, strategy, historical_data)
        assert isinstance(result, BacktestResult)


class TestModels:
    """Test data models."""

    def test_backtest_metadata(self) -> None:
        metadata = BacktestMetadata(name="Test")
        assert metadata.name == "Test"
        assert metadata.version == "1.0"

    def test_backtest_config(self) -> None:
        config = BacktestConfig()
        assert config.initial_capital == 1_000_000.0
        assert config.commission == 0.0003

    def test_backtest_definition(self) -> None:
        definition = BacktestDefinition(
            metadata=BacktestMetadata(name="Test"),
            config=BacktestConfig(),
        )
        assert definition.metadata.name == "Test"

    def test_order(self) -> None:
        order = Order(
            order_id="ORDER_1",
            symbol="RELIANCE",
            order_type=OrderType.MARKET,
            side=PositionSide.LONG,
            quantity=10,
            price=2000.0,
        )
        assert order.order_id == "ORDER_1"
        assert order.status == OrderStatus.PENDING

    def test_trade(self) -> None:
        trade = Trade(
            trade_id="TRADE_1",
            symbol="RELIANCE",
            quantity=10,
            entry_price=2000.0,
            exit_price=2100.0,
            pnl=1000.0,
        )
        assert trade.trade_id == "TRADE_1"
        assert trade.pnl == 1000.0

    def test_position(self) -> None:
        position = Position(
            symbol="RELIANCE",
            quantity=10,
            average_cost=2000.0,
            current_price=2100.0,
            unrealized_pnl=1000.0,
        )
        assert position.symbol == "RELIANCE"
        assert position.unrealized_pnl == 1000.0

    def test_portfolio_snapshot(self) -> None:
        snapshot = PortfolioSnapshot(
            cash=500000,
            holdings_value=500000,
            total_equity=1000000,
        )
        assert snapshot.total_equity == 1000000

    def test_equity_point(self) -> None:
        point = EquityPoint(
            date=datetime(2023, 1, 1),
            equity=100000,
            cash=50000,
        )
        assert point.equity == 100000

    def test_drawdown_point(self) -> None:
        point = DrawdownPoint(
            date=datetime(2023, 1, 1),
            drawdown=-0.05,
            peak_equity=100000,
        )
        assert point.drawdown == -0.05

    def test_performance_metrics(self) -> None:
        metrics = PerformanceMetrics(cagr=0.15, sharpe_ratio=1.2)
        assert metrics.cagr == 0.15
        assert metrics.sharpe_ratio == 1.2

    def test_backtest_statistics(self) -> None:
        stats = BacktestStatistics(total_orders=10, filled_orders=8)
        assert stats.total_orders == 10
        assert stats.filled_orders == 8

    def test_backtest_result(self) -> None:
        result = BacktestResult(
            strategy_name="Test",
            config=BacktestConfig(),
        )
        assert result.strategy_name == "Test"


class TestExceptions:
    """Test exception hierarchy."""

    def test_backtest_error(self) -> None:
        with pytest.raises(BacktestError):
            raise BacktestError("test")

    def test_insufficient_data_error(self) -> None:
        with pytest.raises(InsufficientDataError):
            raise InsufficientDataError("test")

    def test_invalid_order_error(self) -> None:
        with pytest.raises(InvalidOrderError):
            raise InvalidOrderError("test")

    def test_order_execution_error(self) -> None:
        with pytest.raises(OrderExecutionError):
            raise OrderExecutionError("ORDER_1", "test")

    def test_insufficient_cash_error(self) -> None:
        with pytest.raises(InsufficientCashError):
            raise InsufficientCashError(1000.0, 500.0)

    def test_insufficient_shares_error(self) -> None:
        with pytest.raises(InsufficientSharesError):
            raise InsufficientSharesError("RELIANCE", 10, 5)

    def test_position_not_found_error(self) -> None:
        with pytest.raises(PositionNotFoundError):
            raise PositionNotFoundError("RELIANCE")

    def test_invalid_backtest_config_error(self) -> None:
        with pytest.raises(InvalidBacktestConfigError):
            raise InvalidBacktestConfigError("test")

    def test_empty_universe_error(self) -> None:
        with pytest.raises(EmptyUniverseError):
            raise EmptyUniverseError()

    def test_strategy_error(self) -> None:
        with pytest.raises(StrategyError):
            raise StrategyError("test")


class TestIntegration:
    """Integration tests for complete backtesting flow."""

    def test_complete_backtest_flow(self) -> None:
        config = _create_config(symbols=("RELIANCE",))
        definition = BacktestDefinition(
            metadata=BacktestMetadata(name="IntegrationTest"),
            config=config,
        )
        historical_data = _create_historical_data("RELIANCE", days=10)
        engine = BacktestFactory.create(config=config)

        def strategy(data: dict) -> str:
            return "BUY"

        result = engine.run(definition, strategy, {"RELIANCE": historical_data})
        assert isinstance(result, BacktestResult)
        assert result.strategy_name == "IntegrationTest"
        assert len(result.equity_curve) == 10

    def test_multi_symbol_backtest_flow(self) -> None:
        config = _create_config()
        definition = BacktestDefinition(
            metadata=BacktestMetadata(name="MultiSymbolTest"),
            config=config,
        )
        historical_data = _create_multi_symbol_data(days=10)
        engine = BacktestFactory.create(config=config)

        def strategy(data: dict) -> str:
            return "HOLD"

        result = engine.run(definition, strategy, historical_data)
        assert isinstance(result, BacktestResult)
        assert result.statistics.symbols_processed == config.symbols

    def test_report_generation(self) -> None:
        config = _create_config(symbols=("RELIANCE",))
        definition = BacktestDefinition(
            metadata=BacktestMetadata(name="ReportTest"),
            config=config,
        )
        historical_data = _create_historical_data("RELIANCE", days=5)
        engine = BacktestFactory.create(config=config)

        def strategy(data: dict) -> str:
            return "BUY"

        result = engine.run(definition, strategy, {"RELIANCE": historical_data})
        report = BacktestReport(result)
        full_report = report.full_report()
        assert "strategy_name" in full_report
        assert "trade_summary" in full_report
