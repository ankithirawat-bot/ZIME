"""
Repository Registry.

Maps DatasetType to Repository implementations.  No if/elif dispatch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.storage.exceptions import RepositoryNotFoundError
from backend.storage.models import DatasetType

if TYPE_CHECKING:
    from backend.storage.repository import Repository


class RepositoryRegistry:
    """Registry mapping DatasetType to Repository instances.

    Repositories register which dataset types they support.
    The StorageEngine resolves the correct repository through this registry.
    """

    def __init__(self) -> None:
        self._repositories: dict[str, Repository] = {}
        self._type_map: dict[DatasetType, str] = {}

    def register(self, repository: Repository, dataset_types: tuple[DatasetType, ...]) -> None:
        """Register a repository for one or more dataset types.

        Args:
            repository:   Repository instance.
            dataset_types: Dataset types this repository supports.
        """
        name = repository.__class__.__name__
        self._repositories[name] = repository
        for dt in dataset_types:
            self._type_map[dt] = name

    def resolve(self, dataset_type: DatasetType) -> Repository:
        """Resolve the repository for a dataset type.

        Args:
            dataset_type: Dataset type to resolve.

        Returns:
            Repository instance.

        Raises:
            RepositoryNotFoundError: If no repository is registered.
        """
        name = self._type_map.get(dataset_type)
        if name is None:
            raise RepositoryNotFoundError(dataset_type.value)
        return self._repositories[name]

    def resolve_by_name(self, name: str) -> Repository:
        """Resolve a repository by class name.

        Args:
            name: Repository class name.

        Returns:
            Repository instance.

        Raises:
            RepositoryNotFoundError: If repository is not registered.
        """
        repo = self._repositories.get(name)
        if repo is None:
            raise RepositoryNotFoundError(name)
        return repo

    def supported_dataset_types(self, name: str) -> tuple[DatasetType, ...]:
        """Return dataset types supported by a repository.

        Args:
            name: Repository class name.

        Returns:
            Tuple of supported dataset types.

        Raises:
            RepositoryNotFoundError: If repository is not registered.
        """
        if name not in self._repositories:
            raise RepositoryNotFoundError(name)
        return tuple(
            dt for dt, repo_name in self._type_map.items() if repo_name == name
        )

    def available_repositories(self) -> tuple[str, ...]:
        """Return all registered repository names.

        Returns:
            Tuple of repository names.
        """
        return tuple(self._repositories.keys())

    def has_repository(self, name: str) -> bool:
        """Check if a repository is registered.

        Args:
            name: Repository class name.

        Returns:
            True if registered.
        """
        return name in self._repositories

    def has_type(self, dataset_type: DatasetType) -> bool:
        """Check if a dataset type has a registered repository.

        Args:
            dataset_type: Dataset type to check.

        Returns:
            True if a repository is registered for this type.
        """
        return dataset_type in self._type_map
