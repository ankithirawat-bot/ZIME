"""Portfolio constraints.

Validates portfolio against configurable constraints.
"""

from __future__ import annotations

from backend.portfolio.exceptions import ConstraintViolationError
from backend.portfolio.models import PortfolioConfig, PortfolioPosition


class ConstraintValidator:
    """Validates portfolio against configurable constraints.

    Each constraint is independently testable.
    """

    def __init__(self, config: PortfolioConfig) -> None:
        """Initialize the constraint validator.

        Args:
            config: Portfolio configuration.
        """
        self._config = config

    @property
    def config(self) -> PortfolioConfig:
        """Access the configuration."""
        return self._config

    def validate_all(
        self,
        positions: list[PortfolioPosition],
        cash: float,
        total_equity: float,
    ) -> list[ConstraintViolationError]:
        """Validate all constraints.

        Args:
            positions:    Current positions.
            cash:         Available cash.
            total_equity: Total portfolio equity.

        Returns:
            List of constraint violations (empty if all pass).
        """
        violations = []

        try:
            self.check_position_count(positions)
        except ConstraintViolationError as e:
            violations.append(e)

        try:
            self.check_position_sizes(positions, total_equity)
        except ConstraintViolationError as e:
            violations.append(e)

        try:
            self.check_cash_reserve(cash, total_equity)
        except ConstraintViolationError as e:
            violations.append(e)

        try:
            self.check_sector_exposure(positions, total_equity)
        except ConstraintViolationError as e:
            violations.append(e)

        try:
            self.check_stock_exposure(positions, total_equity)
        except ConstraintViolationError as e:
            violations.append(e)

        return violations

    def check_position_count(self, positions: list[PortfolioPosition]) -> None:
        """Check position count constraints.

        Args:
            positions: Current positions.

        Raises:
            ConstraintViolationError: If constraint violated.
        """
        active = [p for p in positions if p.quantity > 0]
        count = len(active)

        if count > self._config.max_positions:
            raise ConstraintViolationError(
                "max_positions",
                f"Too many positions: {count} > {self._config.max_positions}",
            )

        if count < self._config.min_positions:
            raise ConstraintViolationError(
                "min_positions",
                f"Too few positions: {count} < {self._config.min_positions}",
            )

    def check_position_sizes(
        self,
        positions: list[PortfolioPosition],
        total_equity: float,
    ) -> None:
        """Check position size constraints.

        Args:
            positions:    Current positions.
            total_equity: Total portfolio equity.

        Raises:
            ConstraintViolationError: If constraint violated.
        """
        if total_equity <= 0:
            return

        for pos in positions:
            if pos.quantity <= 0:
                continue

            weight = pos.market_value / total_equity

            if weight > self._config.max_position_size:
                raise ConstraintViolationError(
                    "max_position_size",
                    f"Position {pos.symbol} too large: {weight:.2%} > {self._config.max_position_size:.2%}",
                )

            if weight < self._config.min_position_size and weight > 0:
                raise ConstraintViolationError(
                    "min_position_size",
                    f"Position {pos.symbol} too small: {weight:.2%} < {self._config.min_position_size:.2%}",
                )

    def check_cash_reserve(self, cash: float, total_equity: float) -> None:
        """Check cash reserve constraint.

        Args:
            cash:         Available cash.
            total_equity: Total portfolio equity.

        Raises:
            ConstraintViolationError: If constraint violated.
        """
        if total_equity <= 0:
            return

        cash_pct = cash / total_equity
        required_reserve = self._config.cash_reserve

        if cash_pct < required_reserve:
            raise ConstraintViolationError(
                "cash_reserve",
                f"Cash too low: {cash_pct:.2%} < {required_reserve:.2%}",
            )

    def check_sector_exposure(
        self,
        positions: list[PortfolioPosition],
        total_equity: float,
    ) -> None:
        """Check sector exposure constraint.

        Args:
            positions:    Current positions.
            total_equity: Total portfolio equity.

        Raises:
            ConstraintViolationError: If constraint violated.
        """
        if total_equity <= 0:
            return

        sector_values: dict[str, float] = {}
        for pos in positions:
            if pos.quantity > 0:
                sector = pos.sector or "Unknown"
                sector_values[sector] = (
                    sector_values.get(sector, 0.0) + pos.market_value
                )

        for sector, value in sector_values.items():
            exposure = value / total_equity
            if exposure > self._config.max_sector_exposure:
                raise ConstraintViolationError(
                    "max_sector_exposure",
                    f"Sector {sector} exposure too high: {exposure:.2%} > {self._config.max_sector_exposure:.2%}",
                )

    def check_stock_exposure(
        self,
        positions: list[PortfolioPosition],
        total_equity: float,
    ) -> None:
        """Check single stock exposure constraint.

        Args:
            positions:    Current positions.
            total_equity: Total portfolio equity.

        Raises:
            ConstraintViolationError: If constraint violated.
        """
        if total_equity <= 0:
            return

        for pos in positions:
            if pos.quantity <= 0:
                continue

            exposure = pos.market_value / total_equity
            if exposure > self._config.max_stock_exposure:
                raise ConstraintViolationError(
                    "max_stock_exposure",
                    f"Stock {pos.symbol} exposure too high: {exposure:.2%} > {self._config.max_stock_exposure:.2%}",
                )

    def check_liquidity(
        self,
        symbol: str,
        liquidity: float,
    ) -> None:
        """Check liquidity threshold for a symbol.

        Args:
            symbol:     Ticker symbol.
            liquidity:  Liquidity measure.

        Raises:
            ConstraintViolationError: If constraint violated.
        """
        if liquidity < self._config.liquidity_threshold:
            raise ConstraintViolationError(
                "liquidity_threshold",
                f"Liquidity for {symbol} too low: {liquidity:.4f} < {self._config.liquidity_threshold:.4f}",
            )
