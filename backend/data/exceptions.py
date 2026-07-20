"""
Market Data Platform exceptions.

Domain-specific exceptions for data ingestion errors.
"""


class DataPlatformError(Exception):
    """Base exception for all data platform errors."""


class UnsupportedProviderError(DataPlatformError):
    """Raised when a requested provider is not registered."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        super().__init__(f"Provider not registered: {provider}")


class UnsupportedDataTypeError(DataPlatformError):
    """Raised when a provider does not support the requested data type."""

    def __init__(self, data_type: str, provider: str) -> None:
        self.data_type = data_type
        self.provider = provider
        super().__init__(
            f"Provider '{provider}' does not support data type: {data_type}"
        )


class InvalidRequestError(DataPlatformError):
    """Raised when a DataRequest fails structural validation."""

    def __init__(self, message: str, fields: tuple[str, ...] = ()) -> None:
        self.fields = fields
        super().__init__(message)


class ValidationError(DataPlatformError):
    """Raised when data validation fails."""

    def __init__(
        self,
        message: str,
        errors: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
    ) -> None:
        self.errors = errors
        self.warnings = warnings
        super().__init__(message)
