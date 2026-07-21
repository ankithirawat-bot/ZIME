"""Portfolio position management.

Handles opening, adding, reducing, and closing positions.
"""

from __future__ import annotations

from datetime import datetime

from backend.portfolio.exceptions import (
    InsufficientFundsError,
    PositionNotFoundError,
)
from backend.portfolio.models import (
    PortfolioConfig,
    PortfolioPosition,
)


class PositionManager:
    """Manages portfolio positions.

    Tracks positions, average cost, P/L, and holding periods.
    """

    def __init__(self, config: PortfolioConfig) -> None:
        """Initialize the position manager.

        Args:
            config: Portfolio configuration.
        """
        self._config = config
        self._positions: dict[str, _PositionState] = {}

    @property
    def positions(self) -> dict[str, _PositionState]:
        """Access position states."""
        return self._positions

    def open_position(
        self,
        symbol: str,
        quantity: int,
        price: float,
        sector: str = "",
    ) -> PortfolioPosition:
        """Open a new position.

        Args:
            symbol:   Ticker symbol.
            quantity: Number of shares.
            price:    Purchase price.
            sector:   Sector classification.

        Returns:
            Updated position.

        Raises:
            PositionNotFoundError: If position already exists.
        """
        if symbol in self._positions:
            return self.add_to_position(symbol, quantity, price)

        self._positions[symbol] = _PositionState(
            symbol=symbol,
            quantity=quantity,
            average_cost=price,
            current_price=price,
            sector=sector,
            entry_date=datetime.now().astimezone(),
        )

        return self.get_position(symbol)

    def add_to_position(
        self,
        symbol: str,
        quantity: int,
        price: float,
    ) -> PortfolioPosition:
        """Add to an existing position.

        Args:
            symbol:   Ticker symbol.
            quantity: Number of shares to add.
            price:    Purchase price.

        Returns:
            Updated position.

        Raises:
            PositionNotFoundError: If position not found.
        """
        if symbol not in self._positions:
            raise PositionNotFoundError(symbol)

        state = self._positions[symbol]
        total_shares = state.quantity + quantity
        if total_shares > 0:
            new_avg_cost = (
                (state.average_cost * state.quantity) + (price * quantity)
            ) / total_shares
        else:
            new_avg_cost = price

        self._positions[symbol] = _PositionState(
            symbol=symbol,
            quantity=total_shares,
            average_cost=new_avg_cost,
            current_price=state.current_price,
            sector=state.sector,
            entry_date=state.entry_date,
            realized_pnl=state.realized_pnl,
        )

        return self.get_position(symbol)

    def reduce_position(
        self,
        symbol: str,
        quantity: int,
        price: float,
    ) -> PortfolioPosition:
        """Reduce an existing position.

        Args:
            symbol:   Ticker symbol.
            quantity: Number of shares to reduce.
            price:    Sale price.

        Returns:
            Updated position.

        Raises:
            PositionNotFoundError: If position not found.
            InsufficientFundsError: If insufficient shares.
        """
        if symbol not in self._positions:
            raise PositionNotFoundError(symbol)

        state = self._positions[symbol]
        if quantity > state.quantity:
            raise InsufficientFundsError(quantity, state.quantity)

        pnl = (price - state.average_cost) * quantity
        new_quantity = state.quantity - quantity

        if new_quantity <= 0:
            self._positions[symbol] = _PositionState(
                symbol=symbol,
                quantity=0,
                average_cost=state.average_cost,
                current_price=price,
                sector=state.sector,
                entry_date=state.entry_date,
                realized_pnl=state.realized_pnl + pnl,
            )
        else:
            self._positions[symbol] = _PositionState(
                symbol=symbol,
                quantity=new_quantity,
                average_cost=state.average_cost,
                current_price=price,
                sector=state.sector,
                entry_date=state.entry_date,
                realized_pnl=state.realized_pnl + pnl,
            )

        return self.get_position(symbol)

    def close_position(
        self,
        symbol: str,
        price: float,
    ) -> PortfolioPosition:
        """Close a position completely.

        Args:
            symbol: Ticker symbol.
            price:  Sale price.

        Returns:
            Final position state.

        Raises:
            PositionNotFoundError: If position not found.
        """
        if symbol not in self._positions:
            raise PositionNotFoundError(symbol)

        state = self._positions[symbol]
        pnl = (price - state.average_cost) * state.quantity

        self._positions[symbol] = _PositionState(
            symbol=symbol,
            quantity=0,
            average_cost=state.average_cost,
            current_price=price,
            sector=state.sector,
            entry_date=state.entry_date,
            realized_pnl=state.realized_pnl + pnl,
        )

        return self.get_position(symbol)

    def update_market_price(self, symbol: str, price: float) -> None:
        """Update market price for a position.

        Args:
            symbol: Ticker symbol.
            price:  Current market price.
        """
        if symbol in self._positions:
            state = self._positions[symbol]
            self._positions[symbol] = _PositionState(
                symbol=symbol,
                quantity=state.quantity,
                average_cost=state.average_cost,
                current_price=price,
                sector=state.sector,
                entry_date=state.entry_date,
                realized_pnl=state.realized_pnl,
            )

    def update_all_prices(self, prices: dict[str, float]) -> None:
        """Update market prices for all positions.

        Args:
            prices: Dictionary of symbol -> price.
        """
        for symbol, price in prices.items():
            self.update_market_price(symbol, price)

    def get_position(self, symbol: str) -> PortfolioPosition:
        """Get a position.

        Args:
            symbol: Ticker symbol.

        Returns:
            PortfolioPosition with current state.
        """
        if symbol not in self._positions:
            raise PositionNotFoundError(symbol)

        state = self._positions[symbol]
        market_value = state.current_price * state.quantity
        unrealized = (state.current_price - state.average_cost) * state.quantity
        unrealized_pct = (
            unrealized / (state.average_cost * state.quantity)
            if state.average_cost * state.quantity > 0
            else 0.0
        )

        holding_period = (datetime.now().astimezone() - state.entry_date).days

        return PortfolioPosition(
            symbol=state.symbol,
            quantity=state.quantity,
            average_cost=state.average_cost,
            current_price=state.current_price,
            market_value=market_value,
            unrealized_pnl=unrealized,
            unrealized_pct=unrealized_pct,
            realized_pnl=state.realized_pnl,
            holding_period=holding_period,
            sector=state.sector,
        )

    def get_all_positions(self) -> list[PortfolioPosition]:
        """Get all positions.

        Returns:
            List of PortfolioPosition.
        """
        positions = []
        for symbol in self._positions:
            try:
                positions.append(self.get_position(symbol))
            except PositionNotFoundError:
                continue
        return positions

    def get_active_symbols(self) -> tuple[str, ...]:
        """Get symbols with active positions.

        Returns:
            Tuple of symbols with quantity > 0.
        """
        return tuple(
            s for s, p in self._positions.items() if p.quantity > 0
        )

    def get_total_value(self) -> float:
        """Get total portfolio value (holdings only).

        Returns:
            Total value of all holdings.
        """
        total = 0.0
        for state in self._positions.values():
            total += state.current_price * state.quantity
        return total

    def get_sector_exposure(self) -> dict[str, float]:
        """Get sector exposure breakdown.

        Returns:
            Dictionary of sector -> exposure.
        """
        total_value = self.get_total_value()
        if total_value <= 0:
            return {}

        sector_values: dict[str, float] = {}
        for state in self._positions.values():
            if state.quantity > 0:
                sector = state.sector or "Unknown"
                sector_values[sector] = (
                    sector_values.get(sector, 0.0)
                    + state.current_price * state.quantity
                )

        return {s: v / total_value for s, v in sector_values.items()}


class _PositionState:
    """Internal position state (mutable)."""

    def __init__(
        self,
        symbol: str,
        quantity: int = 0,
        average_cost: float = 0.0,
        current_price: float = 0.0,
        sector: str = "",
        entry_date: datetime | None = None,
        realized_pnl: float = 0.0,
    ) -> None:
        self.symbol = symbol
        self.quantity = quantity
        self.average_cost = average_cost
        self.current_price = current_price
        self.sector = sector
        self.entry_date = entry_date or datetime.now().astimezone()
        self.realized_pnl = realized_pnl
