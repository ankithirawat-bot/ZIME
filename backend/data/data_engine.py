"""
Data Engine.

Single public API: ``DataEngine.get_data(request) -> DataResponse``.

Resolves the appropriate provider through the registry,
validates the request, fetches raw data, normalizes it,
and returns a canonical DataResponse.
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.data.exceptions import (
    InvalidRequestError,
    UnsupportedProviderError,
)
from backend.data.models import (
    DataRequest,
    DataResponse,
    DataStatus,
    NormalizedData,
)
from backend.data.normalizer import DataNormalizer
from backend.data.provider_registry import ProviderRegistry
from backend.data.validation import validate_request


class DataEngine:
    """Orchestrates data fetching through provider abstraction.

    Uses ProviderRegistry for dependency inversion.  Never calls
    providers directly — always resolves through the registry.

    Flow:
        request -> provider.fetch_raw() -> RawDataResponse
                -> normalizer.normalize() -> NormalizedData
                -> DataResponse (public API)
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        normalizer: DataNormalizer | None = None,
    ) -> None:
        self._registry = registry
        self._normalizer = normalizer or DataNormalizer()

    def get_data(self, request: DataRequest) -> DataResponse:
        """Fetch data for the given request.

        Resolution order:
            1. Validate request structure.
            2. Resolve provider (preference or type-based).
            3. Provider pre-flight validation.
            4. Fetch raw data from provider.
            5. Normalize raw data via DataNormalizer.
            6. Return canonical DataResponse.

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

        raw = provider.fetch_raw(request)
        normalized = self._normalizer.normalize(raw)

        return DataResponse(
            request=request,
            provider=provider.provider_name(),
            timestamp=datetime.now(UTC),
            status=DataStatus.SUCCESS,
            payload=self._normalized_to_payload(normalized),
            metadata=normalized.metadata,
        )

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

    @staticmethod
    def _normalized_to_payload(normalized: NormalizedData) -> tuple[dict[str, object], ...]:
        """Convert normalized records back to dict payload for DataResponse.

        Args:
            normalized: Normalized data.

        Returns:
            Tuple of record dicts.
        """
        result: list[dict[str, object]] = []
        for record in normalized.records:
            if hasattr(record, "__dict__"):
                result.append(record.__dict__)
            elif hasattr(record, "__dataclass_fields__"):
                result.append(
                    {k: getattr(record, k) for k in record.__dataclass_fields__}
                )
            else:
                result.append({"value": record})
        return tuple(result)
