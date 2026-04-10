"""Application module for config settings shims config workflows."""

from __future__ import annotations

import os


class SettingsShimMixin:
    """Represent settings shim mixin data and behavior."""

    @property
    def database_url_sync(self) -> str:
        """Execute database url sync."""
        return self.database.sync_url

    @property
    def database_url_async(self) -> str:
        """Execute database url async."""
        return self.database.async_url

    @property
    def auth0_issuer(self) -> str:
        """Execute auth0 issuer."""
        return self.auth.issuer

    @property
    def auth0_jwks_url(self) -> str:
        """Execute auth0 jwks url."""
        return self.auth.jwks_url

    @property
    def auth0_audience(self) -> str:
        """Execute auth0 audience."""
        return self.auth.audience

    @property
    def auth0_algorithms(self) -> list[str]:
        """Execute auth0 algorithms."""
        return self.auth.algorithms

    def __getattr__(self, name: str):
        if name == "AUTH0_JWKS_URL":
            return self.auth.AUTH0_JWKS_URL
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}"
        )

    def __setattr__(self, name: str, value):
        if name == "AUTH0_JWKS_URL":
            self.auth.AUTH0_JWKS_URL = value
            return
        super().__setattr__(name, value)

    @property
    def dev_auth_bypass_enabled(self) -> bool:
        """Execute dev auth bypass enabled."""
        env_val = os.getenv("DEV_AUTH_BYPASS") or os.getenv("WINOE_DEV_AUTH_BYPASS")
        value = (env_val if env_val is not None else self.DEV_AUTH_BYPASS) or ""
        return value.strip() == "1"
