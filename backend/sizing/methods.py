"""Position sizing methods.

Implementations of all position sizing strategies following the SizingMethod protocol.
"""

from __future__ import annotations

import math

from backend.sizing.models import PositionRequest, PositionSizing, SizingConfig


def _apply_risk_checks(
    shares: float,
    value: float,
    price: float,
    request: PositionRequest,
    config: SizingConfig,
) -> tuple[float, float, float, str]:
    """Apply risk constraints and round lot adjustments."""
    reason = ""
    max_value = request.available_cash * config.max_position_size
    if value > max_value > 0:
        value = max_value
        shares = value / price if price > 0 else 0.0
        reason = "capped by max_position_size"

    min_value = request.account_size * config.min_position_size
    if value < min_value and value > 0:
        value = 0.0
        shares = 0.0
        reason = "below min_position_size"

    if config.round_lot > 1 and shares > 0:
        shares = math.floor(shares / config.round_lot) * config.round_lot
        value = shares * price
        if reason:
            reason += "; rounded to lot size"
        else:
            reason = "rounded to lot size"

    return shares, value, price, reason


class FixedSharesMethod:
    """Fixed number of shares sizing."""

    @property
    def name(self) -> str:
        return "fixed_shares"

    def calculate(
        self,
        request: PositionRequest,
        config: SizingConfig,
    ) -> PositionSizing:
        shares = 1.0
        value = shares * request.price
        weight = value / request.account_size if request.account_size > 0 else 0.0
        shares, value, price, reason = _apply_risk_checks(
            shares, value, request.price, request, config
        )
        return PositionSizing(
            symbol=request.symbol,
            method=self.name,
            shares=shares,
            value=value,
            weight=weight,
            price=request.price,
            reason=reason or f"Fixed {int(shares)} share(s)",
        )


class FixedValueMethod:
    """Fixed monetary value sizing."""

    @property
    def name(self) -> str:
        return "fixed_value"

    def calculate(
        self,
        request: PositionRequest,
        config: SizingConfig,
    ) -> PositionSizing:
        value = min(10000.0, request.available_cash) if request.available_cash > 0 else 10000.0
        shares = value / request.price if request.price > 0 else 0.0
        weight = value / request.account_size if request.account_size > 0 else 0.0
        shares, value, price, reason = _apply_risk_checks(
            shares, value, request.price, request, config
        )
        return PositionSizing(
            symbol=request.symbol,
            method=self.name,
            shares=shares,
            value=value,
            weight=weight,
            price=request.price,
            reason=reason or f"Fixed value {value:,.0f}",
        )


class FixedFractionalMethod:
    """Fixed fraction of capital sizing."""

    @property
    def name(self) -> str:
        return "fixed_fractional"

    def calculate(
        self,
        request: PositionRequest,
        config: SizingConfig,
    ) -> PositionSizing:
        fraction = min(config.max_position_size, 1.0)
        value = request.available_cash * fraction if request.available_cash > 0 else 0.0
        if value <= 0:
            return PositionSizing(
                symbol=request.symbol,
                method=self.name,
                reason="No available cash",
            )
        shares = value / request.price if request.price > 0 else 0.0
        weight = value / request.account_size if request.account_size > 0 else 0.0
        shares, value, price, reason = _apply_risk_checks(
            shares, value, request.price, request, config
        )
        return PositionSizing(
            symbol=request.symbol,
            method=self.name,
            shares=shares,
            value=value,
            weight=weight,
            price=request.price,
            reason=reason or f"Fixed fraction {fraction:.0%} of capital",
        )


class FixedRiskPerTradeMethod:
    """Fixed risk per trade sizing.

    Sizes position so that the maximum loss equals a fixed percentage of capital.
    """

    @property
    def name(self) -> str:
        return "fixed_risk_per_trade"

    def calculate(
        self,
        request: PositionRequest,
        config: SizingConfig,
    ) -> PositionSizing:
        risk_amount = request.account_size * config.risk_per_trade
        if request.price <= 0:
            return PositionSizing(
                symbol=request.symbol,
                method=self.name,
                reason="Invalid price",
            )
        if request.volatility <= 0:
            shares = risk_amount / (request.price * config.risk_per_trade) if config.risk_per_trade > 0 else 0.0
            risk_per_share = request.price * config.risk_per_trade
        else:
            risk_per_share = request.price * request.volatility

        shares = risk_amount / risk_per_share if risk_per_share > 0 else 0.0
        value = shares * request.price
        weight = value / request.account_size if request.account_size > 0 else 0.0
        shares, value, price, reason = _apply_risk_checks(
            shares, value, request.price, request, config
        )
        return PositionSizing(
            symbol=request.symbol,
            method=self.name,
            shares=shares,
            value=value,
            weight=weight,
            price=request.price,
            risk_amount=risk_amount,
            risk_percentage=config.risk_per_trade,
            reason=reason or f"Risk {config.risk_per_trade:.1%} per trade ({risk_amount:,.0f})",
        )


class PercentageOfEquityMethod:
    """Percentage of equity sizing."""

    @property
    def name(self) -> str:
        return "percentage_of_equity"

    def calculate(
        self,
        request: PositionRequest,
        config: SizingConfig,
    ) -> PositionSizing:
        pct = min(config.max_position_size, 1.0)
        base = request.portfolio_value if request.portfolio_value > 0 else request.account_size
        value = base * pct
        shares = value / request.price if request.price > 0 else 0.0
        weight = pct
        shares, value, price, reason = _apply_risk_checks(
            shares, value, request.price, request, config
        )
        return PositionSizing(
            symbol=request.symbol,
            method=self.name,
            shares=shares,
            value=value,
            weight=weight,
            price=request.price,
            reason=reason or f"{pct:.1%} of equity ({base:,.0f})",
        )


class KellyCriterionMethod:
    """Full Kelly Criterion sizing.

    f* = (p * b - q) / b  where p = win_rate, q = 1-p, b = avg_win/avg_loss
    """

    @property
    def name(self) -> str:
        return "kelly_criterion"

    def calculate(
        self,
        request: PositionRequest,
        config: SizingConfig,
    ) -> PositionSizing:
        if request.win_rate <= 0 or request.win_rate >= 1:
            return PositionSizing(
                symbol=request.symbol,
                method=self.name,
                reason="Invalid win rate for Kelly",
            )
        if request.avg_loss <= 0:
            return PositionSizing(
                symbol=request.symbol,
                method=self.name,
                reason="Invalid avg loss for Kelly",
            )
        b = request.avg_win / request.avg_loss if request.avg_loss > 0 else 0.0
        q = 1.0 - request.win_rate
        if b <= 0:
            return PositionSizing(
                symbol=request.symbol,
                method=self.name,
                reason="Invalid odds ratio for Kelly",
            )
        fraction = (request.win_rate * b - q) / b
        fraction = max(0.0, min(fraction, config.max_position_size))
        value = request.available_cash * fraction if request.available_cash > 0 else 0.0
        if value <= 0:
            return PositionSizing(
                symbol=request.symbol,
                method=self.name,
                reason="Kelly fraction is zero or negative",
            )
        shares = value / request.price if request.price > 0 else 0.0
        weight = value / request.account_size if request.account_size > 0 else 0.0
        shares, value, price, reason = _apply_risk_checks(
            shares, value, request.price, request, config
        )
        return PositionSizing(
            symbol=request.symbol,
            method=self.name,
            shares=shares,
            value=value,
            weight=weight,
            price=request.price,
            confidence=min(1.0, fraction / config.max_position_size) if config.max_position_size > 0 else 1.0,
            reason=reason or f"Kelly fraction {fraction:.2%}",
        )


class FractionalKellyMethod:
    """Fractional Kelly Criterion sizing.

    Uses a fraction of the full Kelly recommendation.
    """

    @property
    def name(self) -> str:
        return "fractional_kelly"

    def calculate(
        self,
        request: PositionRequest,
        config: SizingConfig,
    ) -> PositionSizing:
        if request.win_rate <= 0 or request.win_rate >= 1:
            return PositionSizing(
                symbol=request.symbol,
                method=self.name,
                reason="Invalid win rate for Kelly",
            )
        if request.avg_loss <= 0:
            return PositionSizing(
                symbol=request.symbol,
                method=self.name,
                reason="Invalid avg loss for Kelly",
            )
        b = request.avg_win / request.avg_loss if request.avg_loss > 0 else 0.0
        q = 1.0 - request.win_rate
        if b <= 0:
            return PositionSizing(
                symbol=request.symbol,
                method=self.name,
                reason="Invalid odds ratio for Kelly",
            )
        full_kelly = (request.win_rate * b - q) / b
        fraction = full_kelly * config.kelly_fraction
        fraction = max(0.0, min(fraction, config.max_position_size))
        value = request.available_cash * fraction if request.available_cash > 0 else 0.0
        if value <= 0:
            return PositionSizing(
                symbol=request.symbol,
                method=self.name,
                reason="Kelly fraction is zero or negative",
            )
        shares = value / request.price if request.price > 0 else 0.0
        weight = value / request.account_size if request.account_size > 0 else 0.0
        shares, value, price, reason = _apply_risk_checks(
            shares, value, request.price, request, config
        )
        return PositionSizing(
            symbol=request.symbol,
            method=self.name,
            shares=shares,
            value=value,
            weight=weight,
            price=request.price,
            confidence=min(1.0, fraction / config.max_position_size) if config.max_position_size > 0 else 1.0,
            reason=reason or f"Fractional Kelly ({config.kelly_fraction:.0%}): {fraction:.2%}",
        )


class ATRPositionSizingMethod:
    """ATR-based position sizing.

    Position size = (account * risk_per_trade) / (ATR * atr_multiplier)
    """

    @property
    def name(self) -> str:
        return "atr_position_sizing"

    def calculate(
        self,
        request: PositionRequest,
        config: SizingConfig,
    ) -> PositionSizing:
        if request.atr <= 0:
            return PositionSizing(
                symbol=request.symbol,
                method=self.name,
                reason="ATR is zero or unavailable",
            )
        risk_amount = request.account_size * config.risk_per_trade
        risk_per_share = request.atr * config.atr_multiplier
        shares = risk_amount / risk_per_share if risk_per_share > 0 else 0.0
        value = shares * request.price
        weight = value / request.account_size if request.account_size > 0 else 0.0
        risk_pct = config.risk_per_trade
        shares, value, price, reason = _apply_risk_checks(
            shares, value, request.price, request, config
        )
        return PositionSizing(
            symbol=request.symbol,
            method=self.name,
            shares=shares,
            value=value,
            weight=weight,
            price=request.price,
            risk_amount=risk_amount,
            risk_percentage=risk_pct,
            reason=reason or f"ATR {request.atr:.4f} x {config.atr_multiplier:.0f} risk {risk_amount:,.0f}",
        )


class VolatilityTargetingMethod:
    """Volatility targeting position sizing.

    Position size = (vol_target / position_volatility) * capital_fraction
    """

    @property
    def name(self) -> str:
        return "volatility_targeting"

    def calculate(
        self,
        request: PositionRequest,
        config: SizingConfig,
    ) -> PositionSizing:
        if request.volatility <= 0:
            return PositionSizing(
                symbol=request.symbol,
                method=self.name,
                reason="Volatility is zero or unavailable",
            )
        vol_ratio = config.vol_target / request.volatility
        fraction = min(vol_ratio, config.max_position_size)
        value = request.available_cash * fraction if request.available_cash > 0 else 0.0
        shares = value / request.price if request.price > 0 else 0.0
        weight = value / request.account_size if request.account_size > 0 else 0.0
        shares, value, price, reason = _apply_risk_checks(
            shares, value, request.price, request, config
        )
        return PositionSizing(
            symbol=request.symbol,
            method=self.name,
            shares=shares,
            value=value,
            weight=weight,
            price=request.price,
            reason=reason or f"Vol target {config.vol_target:.0%} / {request.volatility:.0%} = {fraction:.2%}",
        )


class EqualRiskContributionMethod:
    """Equal risk contribution sizing.

    Allocates capital so each position contributes equal risk.
    """

    @property
    def name(self) -> str:
        return "equal_risk_contribution"

    def calculate(
        self,
        request: PositionRequest,
        config: SizingConfig,
    ) -> PositionSizing:
        if request.volatility <= 0:
            return PositionSizing(
                symbol=request.symbol,
                method=self.name,
                reason="Volatility is zero or unavailable",
            )
        risk_budget = config.equal_risk_vol_target
        fraction = risk_budget / request.volatility if request.volatility > 0 else 0.0
        fraction = min(fraction, config.max_position_size)
        value = request.available_cash * fraction if request.available_cash > 0 else 0.0
        shares = value / request.price if request.price > 0 else 0.0
        weight = value / request.account_size if request.account_size > 0 else 0.0
        shares, value, price, reason = _apply_risk_checks(
            shares, value, request.price, request, config
        )
        return PositionSizing(
            symbol=request.symbol,
            method=self.name,
            shares=shares,
            value=value,
            weight=weight,
            price=request.price,
            reason=reason or f"ERC vol {config.equal_risk_vol_target:.0%} / {request.volatility:.0%} = {fraction:.2%}",
        )
