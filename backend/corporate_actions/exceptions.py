"""
Corporate Actions exceptions.

Domain-specific errors for the corporate actions platform.
"""


class CorporateActionError(Exception):
    """Base exception for all corporate action errors."""


class UnsupportedActionTypeError(CorporateActionError):
    """Raised when an action type is not supported."""

    def __init__(self, action_type: str) -> None:
        self.action_type = action_type
        super().__init__(f"Unsupported corporate action type: {action_type}")


class InvalidActionError(CorporateActionError):
    """Raised when a corporate action fails validation."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DuplicateActionError(CorporateActionError):
    """Raised when a corporate action duplicates an existing event."""

    def __init__(self, symbol: str, action_type: str, effective_date: str) -> None:
        self.symbol = symbol
        self.action_type = action_type
        self.effective_date = effective_date
        super().__init__(
            f"Duplicate corporate action: {symbol} {action_type} on {effective_date}"
        )


class OverlappingActionError(CorporateActionError):
    """Raised when corporate actions overlap in an incompatible way."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
