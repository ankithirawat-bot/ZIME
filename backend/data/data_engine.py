"""
Data Engine.

Single public API: ``DataEngine.get_data(request) -> DataResponse``.

Resolves the appropriate provider through the registry,
validates the request, fetches data, and validates the response.
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.data.exceptions import (
    InvalidRequestError,
    UnsupportedProviderError,
)
from backend.data.models import DataRequest, DataResponse, DataStatus
from backend.data.provider_registry import ProviderRegistry
from backend.data.validation import validate_request


class DataEngine:
    """Orchestrates data fetching through provider abstraction.

    Uses ProviderRegistry for dependency inversion.  Never calls
    providers directly — always resolves through the registry.
    """

    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def get_data(self, request: DataRequest) -> DataResponse:
        """Fetch data for the given request.

        Resolution order:
            1. Validate request structure.
            2. Resolve provider (preference or type-based).
            3. Provider pre-flight validation.
            4. Fetch data.
            5. Validate response.

        Args:
            request: Data request.

        Returns:
            DataResponse with data or error status.
        """
        validation = validate_request(request)
        if not validation.valid:
            raise InvalidRequestError(
                f"Invalid request: {'; '.join(validation.errors)}",
                fields=validation.missing_fields,
            )

        provider = self._resolve_provider(request)
        if not provider.validate(request):
            return DataResponse(
                request=request,
                provider=provider.provider_name(),
                timestamp=datetime.now(UTC),
                status=DataStatus.FAILED,
                metadata={"error": "Provider rejected request"},
            )

        return provider.fetch(request)

    def _resolve_provider(self, request: DataRequest):
        """Resolve the provider for a request.

        Uses provider_preference if set, otherwise resolves by data_type.
        """
        if request.provider_preference:
            try:
                return self._registry.resolve_by_name(request.provider_preference)
            except UnsupportedProviderError:
                return self._registry.resolve(request.data_type)
        return self._registry.resolve(request.data_type)
