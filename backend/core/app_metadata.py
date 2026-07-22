"""
Application metadata — single source of truth for FastAPI metadata.

Reads the project version from ``pyproject.toml`` so that no version
literal is duplicated in application code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PROJECT_FILE = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _read_project_version() -> str:
    """Read the ``version`` field from ``pyproject.toml``.

    Returns:
        Version string (e.g. ``"1.0.0"``) or ``"0.0.0"`` on failure.
    """
    try:
        import tomllib

        with _PROJECT_FILE.open("rb") as f:
            data = tomllib.load(f)
        return str(data.get("project", {}).get("version", "0.0.0"))
    except Exception:
        return "0.0.0"


@dataclass(frozen=True)
class AppMetadata:
    """Immutable application metadata used by FastAPI.

    Attributes:
        name:        Short application name.
        version:     Semantic version (read from ``pyproject.toml``).
        description: Human-readable application description.
        api_title:   Title presented in the OpenAPI / Swagger UI.
        docs_url:    Path for Swagger UI (``/docs``).
        redoc_url:   Path for ReDoc (``/redoc``).
        openapi_url: Path for the OpenAPI schema (``/openapi.json``).
        contact:     Optional contact dict for OpenAPI.
        license_info: Optional license dict for OpenAPI.
    """

    name: str = "ZIME"
    version: str = "0.0.0"
    description: str = "Evidence-driven investment research platform"
    api_title: str = "ZIME API"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    contact: dict[str, Any] | None = None
    license_info: dict[str, Any] | None = None


# Module-level singleton populated once at import time.
_METADATA: AppMetadata | None = None


def get_app_metadata() -> AppMetadata:
    """Return the application metadata singleton.

    The version is read from ``pyproject.toml`` on first call and cached
    thereafter.

    Returns:
        AppMetadata populated with project values.
    """
    global _METADATA
    if _METADATA is None:
        _METADATA = AppMetadata(version=_read_project_version())
    return _METADATA
