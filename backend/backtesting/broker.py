"""Backtesting broker.

Simulates realistic order execution with transaction costs.
"""

from __future__ import annotations

from datetime import datetime

from backend.backtesting.exceptions import (
    InsufficientCashError,
    InsufficientSharesError,
    InvalidOrderError,
    OrderExecutionError,
)
from backend.backtesting.models import (
    BacktestConfig,
    Order,
    OrderStatus,
    OrderType,
    PositionSide,
)


class Broker:
    """Simulates realistic order execution with transaction costs.

    Supports market, limit, and stop orders with configurable costs.
    """

    def __init__(self, config: BacktestConfig | None = None) -> None:
        """Initialize the broker.

        Args:
            config: Backtest configuration with cost parameters.
        """
        self._config = config or BacktestConfig()

    @property
    def config(self) -> BacktestConfig:
        """Access the broker configuration."""
        return self._config

    def execute_order(
        self,
        order: Order,
        current_price: float,
        cash: float,
        holdings: dict[str, int],
    ) -> Order:
        """Execute an order at the current market price.

        Args:
            order:         Order to execute.
            current_price: Current market price.
            cash:          Available cash.
            holdings:      Current holdings (symbol -> quantity).

        Returns:
            Updated order with fill information.

        Raises:
            InvalidOrderError: If the order is invalid.
            InsufficientCashError: If insufficient cash for buy.
            InsufficientSharesError: If insufficient shares for sell.
            OrderExecutionError: If execution fails.
        """
        if order.quantity <= 0:
            raise InvalidOrderError(f"Quantity must be positive, got {order.quantity}")

        if current_price <= 0:
            raise InvalidOrderError(f"Price must be positive, got {current_price}")

        if order.order_type == OrderType.MARKET:
            return self._execute_market_order(order, current_price, cash, holdings)
        elif order.order_type == OrderType.LIMIT:
            return self._execute_limit_order(order, current_price, cash, holdings)
        elif order.order_type == OrderType.STOP:
            return self._execute_stop_order(order, current_price, cash, holdings)
        else:
            raise InvalidOrderError(f"Unsupported order type: {order.order_type}")

    def cancel_order(self, order: Order) -> Order:
        """Cancel an order.

        Args:
            order: Order to cancel.

        Returns:
            Updated order with cancelled status.
        """
        if order.status != OrderStatus.PENDING:
            raise OrderExecutionError(
                order.order_id,
                f"Cannot cancel order with status {order.status}",
            )

        return Order(
            order_id=order.order_id,
            symbol=order.symbol,
            order_type=order.order_type,
            side=order.side,
            quantity=order.quantity,
            price=order.price,
            stop_price=order.stop_price,
            created_at=order.created_at,
            status=OrderStatus.CANCELLED,
        )

    def calculate_transaction_cost(self, quantity: int, price: float) -> dict[str, float]:
        """Calculate total transaction cost for a trade.

        Args:
            quantity: Number of shares.
            price:    Price per share.

        Returns:
            Dictionary of cost components.
        """
        trade_value = quantity * price

        brokerage = trade_value * self._config.commission
        stt = trade_value * self._config.stt_rate
        exchange = trade_value * self._config.exchange_rate
        sebi = trade_value * self._config.sebi_rate
        gst = (brokerage + exchange) * self._config.gst_rate
        stamp_duty = trade_value * self._config.stamp_duty_rate
        slippage = trade_value * self._config.slippage

        total = brokerage + stt + exchange + sebi + gst + stamp_duty + slippage

        return {
            "brokerage": brokerage,
            "stt": stt,
            "exchange": exchange,
            "sebi": sebi,
            "gst": gst,
            "stamp_duty": stamp_duty,
            "slippage": slippage,
            "total": total,
        }

    def _execute_market_order(
        self,
        order: Order,
        current_price: float,
        cash: float,
        holdings: dict[str, int],
    ) -> Order:
        """Execute a market order.

        Args:
            order:         Order to execute.
            current_price: Current market price.
            cash:          Available cash.
            holdings:      Current holdings.

        Returns:
            Updated order with fill information.
        """
        fill_price = current_price

        if order.order_id.startswith("BUY"):
            return self._execute_buy(order, fill_price, cash, holdings)
        else:
            return self._execute_sell(order, fill_price, holdings)

    def _execute_limit_order(
        self,
        order: Order,
        current_price: float,
        cash: float,
        holdings: dict[str, int],
    ) -> Order:
        """Execute a limit order.

        For buy limit orders: fills if market price <= limit price.
        For sell limit orders: fills if market price >= limit price.

        Args:
            order:         Order to execute.
            current_price: Current market price.
            cash:          Available cash.
            holdings:      Current holdings.

        Returns:
            Updated order with fill information.
        """
        if order.side == PositionSide.LONG:
            if current_price <= order.price:
                return self._execute_buy(order, order.price, cash, holdings)
            else:
                return Order(
                    order_id=order.order_id,
                    symbol=order.symbol,
                    order_type=order.order_type,
                    side=order.side,
                    quantity=order.quantity,
                    price=order.price,
                    stop_price=order.stop_price,
                    created_at=order.created_at,
                    status=OrderStatus.PENDING,
                )
        else:
            if current_price >= order.price:
                return self._execute_sell(order, order.price, holdings)
            else:
                return Order(
                    order_id=order.order_id,
                    symbol=order.symbol,
                    order_type=order.order_type,
                    side=order.side,
                    quantity=order.quantity,
                    price=order.price,
                    stop_price=order.stop_price,
                    created_at=order.created_at,
                    status=OrderStatus.PENDING,
                )

    def _execute_stop_order(
        self,
        order: Order,
        current_price: float,
        cash: float,
        holdings: dict[str, int],
    ) -> Order:
        """Execute a stop order.

        For buy stop orders: fills if market price >= stop price.
        For sell stop orders: fills if market price <= stop price.

        Args:
            order:         Order to execute.
            current_price: Current market price.
            cash:          Available cash.
            holdings:      Current holdings.

        Returns:
            Updated order with fill information.
        """
        if order.side == PositionSide.LONG:
            if current_price >= order.stop_price:
                return self._execute_buy(order, current_price, cash, holdings)
            else:
                return Order(
                    order_id=order.order_id,
                    symbol=order.symbol,
                    order_type=order.order_type,
                    side=order.side,
                    quantity=order.quantity,
                    price=order.price,
                    stop_price=order.stop_price,
                    created_at=order.created_at,
                    status=OrderStatus.PENDING,
                )
        else:
            if current_price <= order.stop_price:
                return self._execute_sell(order, current_price, holdings)
            else:
                return Order(
                    order_id=order.order_id,
                    symbol=order.symbol,
                    order_type=order.order_type,
                    side=order.side,
                    quantity=order.quantity,
                    price=order.price,
                    stop_price=order.stop_price,
                    created_at=order.created_at,
                    status=OrderStatus.PENDING,
                )

    def _execute_buy(
        self,
        order: Order,
        fill_price: float,
        cash: float,
        holdings: dict[str, int],
    ) -> Order:
        """Execute a buy order.

        Args:
            order:      Order to execute.
            fill_price: Fill price.
            cash:       Available cash.
            holdings:   Current holdings.

        Returns:
            Updated order with fill information.

        Raises:
            InsufficientCashError: If insufficient cash.
        """
        costs = self.calculate_transaction_cost(order.quantity, fill_price)
        total_cost = (order.quantity * fill_price) + costs["total"]

        if total_cost > cash:
            raise InsufficientCashError(total_cost, cash)

        return Order(
            order_id=order.order_id,
            symbol=order.symbol,
            order_type=order.order_type,
            side=order.side,
            quantity=order.quantity,
            price=order.price,
            stop_price=order.stop_price,
            created_at=order.created_at,
            status=OrderStatus.FILLED,
            filled_price=fill_price,
            filled_at=datetime.now().astimezone(),
        )

    def _execute_sell(
        self,
        order: Order,
        fill_price: float,
        holdings: dict[str, int],
    ) -> Order:
        """Execute a sell order.

        Args:
            order:      Order to execute.
            fill_price: Fill price.
            holdings:   Current holdings.

        Returns:
            Updated order with fill information.

        Raises:
            InsufficientSharesError: If insufficient shares.
        """
        current_shares = holdings.get(order.symbol, 0)

        if current_shares < order.quantity:
            raise InsufficientSharesError(
                order.symbol, order.quantity, current_shares
            )

        return Order(
            order_id=order.order_id,
            symbol=order.symbol,
            order_type=order.order_type,
            side=order.side,
            quantity=order.quantity,
            price=order.price,
            stop_price=order.stop_price,
            created_at=order.created_at,
            status=OrderStatus.FILLED,
            filled_price=fill_price,
            filled_at=datetime.now().astimezone(),
        )
