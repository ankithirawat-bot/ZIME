"""Pipeline exception hierarchy."""

from __future__ import annotations


class PipelineError(Exception):
    """Base exception for all pipeline errors."""


class PipelineStageError(PipelineError):
    """Raised when a pipeline stage fails."""

    def __init__(self, stage: str, message: str, *, recoverable: bool = False) -> None:
        self.stage = stage
        self.recoverable = recoverable
        super().__init__(f"Stage '{stage}': {message}")


class ProviderFetchError(PipelineStageError):
    """Raised when data provider fetch fails."""

    def __init__(self, symbol: str, message: str) -> None:
        self.symbol = symbol
        super().__init__("fetch", f"Provider fetch failed for {symbol}: {message}", recoverable=True)


class ValidationError(PipelineStageError):
    """Raised when data validation fails."""

    def __init__(self, symbol: str, message: str) -> None:
        self.symbol = symbol
        super().__init__("validate", f"Validation failed for {symbol}: {message}", recoverable=True)


class NormalizationError(PipelineStageError):
    """Raised when data normalization fails."""

    def __init__(self, symbol: str, message: str) -> None:
        self.symbol = symbol
        super().__init__("normalize", f"Normalization failed for {symbol}: {message}", recoverable=True)


class CorporateActionError(PipelineStageError):
    """Raised when corporate action adjustment fails."""

    def __init__(self, symbol: str, message: str) -> None:
        self.symbol = symbol
        super().__init__("corporate_action", f"Corporate action adjustment failed for {symbol}: {message}", recoverable=True)


class DataQualityError(PipelineStageError):
    """Raised when data quality check fails."""

    def __init__(self, symbol: str, message: str) -> None:
        self.symbol = symbol
        super().__init__("data_quality", f"Data quality check failed for {symbol}: {message}", recoverable=True)


class PersistenceError(PipelineStageError):
    """Raised when data persistence fails."""

    def __init__(self, symbol: str, message: str) -> None:
        self.symbol = symbol
        super().__init__("persist", f"Persistence failed for {symbol}: {message}", recoverable=False)


class DatabaseUnavailableError(PipelineStageError):
    """Raised when database is unavailable (fatal)."""

    def __init__(self, message: str) -> None:
        super().__init__("persist", f"Database unavailable: {message}", recoverable=False)


class SchemaCorruptionError(PipelineStageError):
    """Raised when schema corruption is detected (fatal)."""

    def __init__(self, message: str) -> None:
        super().__init__("persist", f"Schema corruption: {message}", recoverable=False)


class ReportGenerationError(PipelineStageError):
    """Raised when report generation fails."""

    def __init__(self, message: str) -> None:
        super().__init__("report", f"Report generation failed: {message}", recoverable=True)


class PipelineConfigurationError(PipelineError):
    """Raised when pipeline configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Configuration error: {message}")
