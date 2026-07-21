"""
Fundamentals exceptions.

Domain-specific errors for the fundamentals platform.
"""


class FundamentalError(Exception):
    """Base exception for all fundamentals errors."""


class UnsupportedStatementTypeError(FundamentalError):
    """Raised when a statement type is not supported."""

    def __init__(self, statement_type: str) -> None:
        self.statement_type = statement_type
        super().__init__(f"Unsupported fundamental statement type: {statement_type}")


class InvalidFundamentalError(FundamentalError):
    """Raised when a fundamental record fails validation."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DuplicateStatementError(FundamentalError):
    """Raised when a fundamental statement duplicates an existing one."""

    def __init__(self, symbol: str, statement_type: str, period: str) -> None:
        self.symbol = symbol
        self.statement_type = statement_type
        self.period = period
        super().__init__(
            f"Duplicate fundamental statement: {symbol} {statement_type} {period}"
        )


class StatementNotFoundError(FundamentalError):
    """Raised when a requested fundamental statement does not exist."""

    def __init__(self, symbol: str, statement_type: str) -> None:
        self.symbol = symbol
        self.statement_type = statement_type
        super().__init__(
            f"Fundamental statement not found: {symbol} {statement_type}"
        )
