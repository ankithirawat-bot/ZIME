"""Position sizing constraints.

Configurable constraint validation for position sizes, portfolio exposure,
sector limits, and trade minimums.
"""

from __future__ import annotations

from backend.sizing.models import AllocationResult, PositionSizing, SizingConfig


class ConstraintResult:
    """Result of constraint validation.

    Attributes:
        valid:    Whether the constraint is satisfied.
        message:  Human-readable explanation.
        constraint: Constraint name.
    """

    def __init__(self, valid: bool, message: str = "", constraint: str = "") -> None:
        self.valid = valid
        self.message = message
        self.constraint = constraint


class SizingConstraints:
    """Constraint validator for position sizing."""

    @staticmethod
    def check_max_position_size(
        weight: float,
        config: SizingConfig,
    ) -> ConstraintResult:
        """Check maximum position size constraint."""
        if weight > config.max_position_size:
            return ConstraintResult(
                valid=False,
                message=f"Position weight {weight:.2%} exceeds maximum {config.max_position_size:.2%}",
                constraint="max_position_size",
            )
        return ConstraintResult(valid=True, constraint="max_position_size")

    @staticmethod
    def check_min_position_size(
        weight: float,
        config: SizingConfig,
    ) -> ConstraintResult:
        """Check minimum position size constraint."""
        if weight > 0 and weight < config.min_position_size:
            return ConstraintResult(
                valid=False,
                message=f"Position weight {weight:.4f} is below minimum {config.min_position_size:.4f}",
                constraint="min_position_size",
            )
        return ConstraintResult(valid=True, constraint="min_position_size")

    @staticmethod
    def check_max_portfolio_exposure(
        total_exposure: float,
        config: SizingConfig,
    ) -> ConstraintResult:
        """Check maximum portfolio exposure constraint."""
        if total_exposure > config.max_portfolio_exposure:
            return ConstraintResult(
                valid=False,
                message=f"Portfolio exposure {total_exposure:.2%} exceeds maximum {config.max_portfolio_exposure:.2%}",
                constraint="max_portfolio_exposure",
            )
        return ConstraintResult(valid=True, constraint="max_portfolio_exposure")

    @staticmethod
    def check_max_sector_exposure(
        sector_exposure: dict[str, float],
        sector: str,
        weight: float,
        config: SizingConfig,
    ) -> ConstraintResult:
        """Check maximum sector exposure constraint."""
        if not sector:
            return ConstraintResult(valid=True, constraint="max_sector_exposure")
        current = sector_exposure.get(sector, 0.0)
        new_exposure = current + weight
        if new_exposure > config.max_sector_exposure:
            return ConstraintResult(
                valid=False,
                message=f"Sector {sector} exposure {new_exposure:.2%} exceeds maximum {config.max_sector_exposure:.2%}",
                constraint="max_sector_exposure",
            )
        return ConstraintResult(valid=True, constraint="max_sector_exposure")

    @staticmethod
    def check_cash_reserve(
        available_cash: float,
        account_size: float,
        config: SizingConfig,
    ) -> ConstraintResult:
        """Check cash reserve constraint."""
        required_reserve = account_size * config.cash_reserve
        if available_cash < required_reserve:
            return ConstraintResult(
                valid=False,
                message=f"Available cash {available_cash:,.0f} is below required reserve {required_reserve:,.0f}",
                constraint="cash_reserve",
            )
        return ConstraintResult(valid=True, constraint="cash_reserve")

    @staticmethod
    def check_max_leverage(
        leverage: float,
        config: SizingConfig,
    ) -> ConstraintResult:
        """Check maximum leverage constraint."""
        if leverage > config.max_leverage:
            return ConstraintResult(
                valid=False,
                message=f"Leverage {leverage:.2f} exceeds maximum {config.max_leverage:.2f}",
                constraint="max_leverage",
            )
        return ConstraintResult(valid=True, constraint="max_leverage")

    @staticmethod
    def check_round_lot(
        shares: float,
        config: SizingConfig,
    ) -> ConstraintResult:
        """Check round lot constraint."""
        if config.round_lot > 1 and shares > 0:
            remainder = shares % config.round_lot
            if abs(remainder) > 0.001:
                return ConstraintResult(
                    valid=False,
                    message=f"Position {shares:.0f} shares not a multiple of lot size {config.round_lot}",
                    constraint="round_lot",
                )
        return ConstraintResult(valid=True, constraint="round_lot")

    @staticmethod
    def check_min_trade_value(
        value: float,
        config: SizingConfig,
    ) -> ConstraintResult:
        """Check minimum trade value constraint."""
        if value > 0 and value < config.min_trade_value:
            return ConstraintResult(
                valid=False,
                message=f"Trade value {value:,.0f} is below minimum {config.min_trade_value:,.0f}",
                constraint="min_trade_value",
            )
        return ConstraintResult(valid=True, constraint="min_trade_value")

    @staticmethod
    def validate_position(
        sizing: PositionSizing,
        sector_exposure: dict[str, float],
        sector: str,
        config: SizingConfig,
    ) -> tuple[ConstraintResult, ...]:
        """Validate a single position against all applicable constraints.

        Args:
            sizing:          Position sizing result.
            sector_exposure: Current sector exposure map.
            sector:          Position sector.
            config:          Sizing configuration.

        Returns:
            Tuple of constraint results.
        """
        results = []
        results.append(SizingConstraints.check_max_position_size(sizing.weight, config))
        results.append(SizingConstraints.check_min_position_size(sizing.weight, config))
        results.append(
            SizingConstraints.check_max_sector_exposure(
                sector_exposure, sector, sizing.weight, config
            )
        )
        results.append(SizingConstraints.check_round_lot(sizing.shares, config))
        results.append(SizingConstraints.check_min_trade_value(sizing.value, config))
        return tuple(results)

    @staticmethod
    def validate_allocation(
        allocation: AllocationResult,
        config: SizingConfig,
    ) -> tuple[ConstraintResult, ...]:
        """Validate the complete allocation.

        Args:
            allocation: Allocation result.
            config:     Sizing configuration.

        Returns:
            Tuple of constraint results.
        """
        results = []
        results.append(
            SizingConstraints.check_max_portfolio_exposure(allocation.exposure, config)
        )
        results.append(
            SizingConstraints.check_cash_reserve(
                allocation.cash_remaining, config.default_account_size, config
            )
        )
        return tuple(results)
