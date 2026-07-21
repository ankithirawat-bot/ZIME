"""
Auth Manager.

Handles Upstox credential management, access token lifecycle,
and token refresh hooks.  Never exposes secrets outside the manager.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class UpstoxCredentials:
    """Immutable Upstox API credentials.

    Attributes:
        api_key:       Application API key.
        api_secret:    Application API secret.
        access_token:  Bearer access token.
        redirect_uri:  OAuth redirect URI.
    """

    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    redirect_uri: str = ""


class AuthManager:
    """Manages Upstox authentication state.

    Responsibilities:
        - Read credentials from configuration.
        - Access token management (set, clear, query).
        - Token refresh hooks.
        - Never expose secrets outside the manager.
    """

    def __init__(
        self,
        credentials: UpstoxCredentials | None = None,
        refresh_fn: Callable[[], str | None] | None = None,
    ) -> None:
        """Initialise the auth manager.

        Args:
            credentials: Optional pre-loaded credentials.
            refresh_fn:  Optional callback that returns a fresh access
                         token or None if refresh fails.
        """
        self._credentials = credentials or UpstoxCredentials()
        self._refresh_fn = refresh_fn

    @property
    def is_authenticated(self) -> bool:
        """True when a valid access token is held."""
        return bool(self._credentials.access_token)

    @property
    def api_key(self) -> str:
        """Return the API key."""
        return self._credentials.api_key

    @property
    def access_token(self) -> str:
        """Return the current access token.

        Tokens are returned as-is.  Callers must not persist them.
        """
        return self._credentials.access_token

    def set_access_token(self, token: str) -> None:
        """Update the access token.

        Args:
            token: New access token.
        """
        self._credentials = UpstoxCredentials(
            api_key=self._credentials.api_key,
            api_secret=self._credentials.api_secret,
            access_token=token,
            redirect_uri=self._credentials.redirect_uri,
        )

    def clear_access_token(self) -> None:
        """Clear the access token (logout)."""
        self._credentials = UpstoxCredentials(
            api_key=self._credentials.api_key,
            api_secret=self._credentials.api_secret,
            access_token="",
            redirect_uri=self._credentials.redirect_uri,
        )

    def refresh_token(self) -> str | None:
        """Attempt to refresh the access token.

        Uses the registered refresh callback if available.

        Returns:
            New access token or None if refresh fails.
        """
        if self._refresh_fn is None:
            return None

        new_token = self._refresh_fn()
        if new_token:
            self.set_access_token(new_token)
        return new_token

    def credentials(self) -> UpstoxCredentials:
        """Return a copy of the current credentials.

        The returned object is frozen and safe to pass around.
        """
        return self._credentials
