"""Backtesting portfolio.

Tracks cash, holdings, positions, and P/L.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.backtesting.broker import Broker
from backend.backtesting.exceptions import (
    InsufficientSharesError,
)
from backend.backtesting.models import (
    BacktestConfig,
    Order,
    OrderStatus,
    PortfolioSnapshot,
    Position,
    PositionSide,
)


@dataclass
class Holding:
    """Internal holding state.

    Attributes:
        symbol:       Ticker symbol.
        quantity:     Number of shares.
        average_cost: Average cost per share.
        realized_pnl: Realized profit/loss.
    """

    symbol: str
    quantity: int = 0
    average_cost: float = 0.0
    realized_pnl: float = 0.0


class Portfolio:
    """Tracks cash, holdings, positions, and P/L.

    Manages the portfolio state throughout a backtest.
    """

    def __init__(self, config: BacktestConfig, broker: Broker | None = None) -> None:
        """Initialize the portfolio.

        Args:
            config: Backtest configuration.
            broker: Broker for order execution.
        """
        self._config = config
        self._broker = broker or Broker(config)
        self._cash = config.initial_capital
        self._holdings: dict[str, Holding] = {}
        self._total_realized_pnl = 0.0
        self._market_prices: dict[str, float] = {}

    @property
    def cash(self) -> float:
        """Available cash."""
        return self._cash

    @property
    def holdings(self) -> dict[str, int]:
        """Current holdings (symbol -> quantity)."""
        return {s: h.quantity for s, h in self._holdings.items() if h.quantity > 0}

    @property
    def total_equity(self) -> float:
        """Total portfolio equity."""
        return self._cash + self._calculate_holdings_value()

    @property
    def unrealized_pnl(self) -> float:
        """Total unrealized P/L."""
        total = 0.0
        for h in self._holdings.values():
            if h.quantity > 0 and h.symbol in self._market_prices:
                price = self._market_prices[h.symbol]
                total += (price - h.average_cost) * h.quantity
        return total

    @property
    def realized_pnl(self) -> float:
        """Total realized P/L."""
        return self._total_realized_pnl

    @property
    def exposure(self) -> float:
        """Portfolio exposure (holdings / total equity)."""
        equity = self.total_equity
        if equity <= 0:
            return 0.0
        return self._calculate_holdings_value() / equity

    def get_positions(self, market_prices: dict[str, float] | None = None) -> list[Position]:
        """Get current positions.

        Args:
            market_prices: Current market prices.

        Returns:
            List of current positions.
        """
        if market_prices is not None:
            self._market_prices = market_prices
        positions = []

        for symbol, holding in self._holdings.items():
            if holding.quantity <= 0:
                continue

            current_price = self._market_prices.get(symbol, holding.average_cost)
            market_value = current_price * holding.quantity
            unrealized = (current_price - holding.average_cost) * holding.quantity
            unrealized_pct = (
                unrealized / (holding.average_cost * holding.quantity)
                if holding.average_cost * holding.quantity > 0
                else 0.0
            )

            positions.append(
                Position(
                    symbol=symbol,
                    side=PositionSide.LONG,
                    quantity=holding.quantity,
                    average_cost=holding.average_cost,
                    current_price=current_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized,
                    unrealized_pct=unrealized_pct,
                    realized_pnl=holding.realized_pnl,
                )
            )

        return positions

    def buy(
        self,
        symbol: str,
        quantity: int,
        price: float,
        market_prices: dict[str, float] | None = None,
    ) -> Order:
        """Buy shares.

        Args:
            symbol:       Ticker symbol.
            quantity:     Number of shares.
            price:        Buy price.
            market_prices: Current market prices for validation.

        Returns:
            Executed order.

        Raises:
            InsufficientCashError: If insufficient cash.
        """
        from backend.backtesting.models import OrderType

        order = Order(
            order_id=f"BUY_{symbol}_{datetime.now().astimezone().timestamp()}",
            symbol=symbol,
            order_type=OrderType.MARKET,
            side=PositionSide.LONG,
            quantity=quantity,
            price=price,
        )

        executed = self._broker.execute_order(
            order, price, self._cash, self.holdings
        )

        if executed.status == OrderStatus.FILLED:
            costs = self._broker.calculate_transaction_cost(quantity, price)
            total_cost = (quantity * price) + costs["total"]

            self._cash -= total_cost

            if symbol in self._holdings:
                holding = self._holdings[symbol]
                total_shares = holding.quantity + quantity
                if total_shares > 0:
                    holding.average_cost = (
                        (holding.average_cost * holding.quantity) + (price * quantity)
                    ) / total_shares
                holding.quantity = total_shares
            else:
                self._holdings[symbol] = Holding(
                    symbol=symbol,
                    quantity=quantity,
                    average_cost=price,
                )

        return executed

    def sell(
        self,
        symbol: str,
        quantity: int,
        price: float,
        market_prices: dict[str, float] | None = None,
    ) -> Order:
        """Sell shares.

        Args:
            symbol:       Ticker symbol.
            quantity:     Number of shares.
            price:        Sell price.
            market_prices: Current market prices for validation.

        Returns:
            Executed order.

        Raises:
            InsufficientSharesError: If insufficient shares.
        """
        from backend.backtesting.models import OrderType

        if symbol not in self._holdings or self._holdings[symbol].quantity < quantity:
            available = self._holdings.get(symbol, Holding(symbol=symbol)).quantity
            raise InsufficientSharesError(symbol, quantity, available)

        order = Order(
            order_id=f"SELL_{symbol}_{datetime.now().astimezone().timestamp()}",
            symbol=symbol,
            order_type=OrderType.MARKET,
            side=PositionSide.LONG,
            quantity=quantity,
            price=price,
        )

        executed = self._broker.execute_order(
            order, price, self._cash, self.holdings
        )

        if executed.status == OrderStatus.FILLED:
            costs = self._broker.calculate_transaction_cost(quantity, price)
            gross_proceeds = quantity * price
            net_proceeds = gross_proceeds - costs["total"]

            self._cash += net_proceeds

            holding = self._holdings[symbol]
            pnl = (price - holding.average_cost) * quantity - costs["total"]
            holding.realized_pnl += pnl
            self._total_realized_pnl += pnl
            holding.quantity -= quantity

        return executed

    def update_market_value(self, symbol: str, price: float) -> None:
        """Update the market value of a position.

        Args:
            symbol: Ticker symbol.
            price:  Current market price.
        """
        if symbol:
            self._market_prices[symbol] = price

    def set_market_prices(self, prices: dict[str, float]) -> None:
        """Set all market prices at once.

        Args:
            prices: Dictionary of symbol -> price.
        """
        self._market_prices = prices

    def close_position(
        self,
        symbol: str,
        price: float,
        market_prices: dict[str, float] | None = None,
    ) -> Order | None:
        """Close a position completely.

        Args:
            symbol:       Ticker symbol.
            price:        Close price.
            market_prices: Current market prices.

        Returns:
            Executed order or None if no position.
        """
        if symbol not in self._holdings or self._holdings[symbol].quantity <= 0:
            return None

        quantity = self._holdings[symbol].quantity
        return self.sell(symbol, quantity, price, market_prices)

    def get_snapshot(
        self,
        timestamp: datetime | None = None,
        market_prices: dict[str, float] | None = None,
    ) -> PortfolioSnapshot:
        """Get a portfolio snapshot.

        Args:
            timestamp:    Snapshot timestamp.
            market_prices: Current market prices.

        Returns:
            PortfolioSnapshot with current state.
        """
        if market_prices is not None:
            self._market_prices = market_prices
        positions = self.get_positions()
        holdings_value = self._calculate_holdings_value()

        return PortfolioSnapshot(
            timestamp=timestamp or datetime.now().astimezone(),
            cash=self._cash,
            holdings_value=holdings_value,
            total_equity=self._cash + holdings_value,
            unrealized_pnl=self.unrealized_pnl,
            realized_pnl=self._total_realized_pnl,
            exposure=self.exposure,
            positions=tuple(positions),
        )

    def _calculate_holdings_value(self) -> float:
        """Calculate total value of holdings."""
        total = 0.0
        for symbol, holding in self._holdings.items():
            if holding.quantity > 0:
                price = self._market_prices.get(symbol, holding.average_cost)
                total += price * holding.quantity
        return total
