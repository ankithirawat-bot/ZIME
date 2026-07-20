"""
Data Normalizer.

Converts RawDataResponse into NormalizedData using registered
DataSource implementations.  No provider-specific business logic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.data.exceptions import UnsupportedDataTypeError
from backend.data.models import DataType, NormalizedData, RawDataResponse

if TYPE_CHECKING:
    from backend.data.datasource import DataSource


class DataNormalizer:
    """Orchestrates normalization of raw provider data.

    Routes RawDataResponse to the correct DataSource based on
    data_type, then wraps the result in NormalizedData.
    """

    def __init__(self) -> None:
        self._sources: dict[DataType, DataSource] = {}

    def register(self, source: DataSource, data_types: tuple[DataType, ...]) -> None:
        """Register a DataSource for one or more data types.

        Args:
            source:    DataSource instance.
            data_types: Data types this source handles.
        """
        for dt in data_types:
            self._sources[dt] = source

    def normalize(self, response: RawDataResponse) -> NormalizedData:
        """Normalize a raw response into canonical data.

        Args:
            response: Raw provider response.

        Returns:
            NormalizedData with canonical records.

        Raises:
            UnsupportedDataTypeError: If no source is registered.
        """
        source = self._sources.get(response.provider_type.data_type)
        if source is None:
            raise UnsupportedDataTypeError(
                response.provider_type.data_type.value, "normalizer"
            )

        records = source.normalize(response)
        return NormalizedData(
            symbol=response.provider_type.symbol,
            exchange=response.provider_type.exchange,
            data_type=response.provider_type.data_type,
            records=records,
            metadata=response.metadata,
        )

    def has_source(self, data_type: DataType) -> bool:
        """Check if a DataSource is registered for a data type.

        Args:
            data_type: Data type to check.

        Returns:
            True if a source is registered.
        """
        return data_type in self._sources

    def registered_types(self) -> tuple[DataType, ...]:
        """Return all data types with registered sources.

        Returns:
            Tuple of supported data types.
        """
        return tuple(self._sources.keys())
