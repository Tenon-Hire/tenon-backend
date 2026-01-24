from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .claims import claim_namespace, claim_uri
from .defaults import DEFAULT_CLAIM_NAMESPACE


class AuthSettings(BaseSettings):
    """Auth-related configuration (Auth0 + JWT compatibility)."""

    AUTH0_DOMAIN: str = ""
    AUTH0_ISSUER: str | None = None
    AUTH0_JWKS_URL: str | None = None
    AUTH0_API_AUDIENCE: str = ""
    AUTH0_ALGORITHMS: str = "RS256"
    AUTH0_LEEWAY_SECONDS: int = 60
    AUTH0_JWKS_CACHE_TTL_SECONDS: int = 3600
    AUTH0_CLAIM_NAMESPACE: str = DEFAULT_CLAIM_NAMESPACE
    AUTH0_EMAIL_CLAIM: str = ""
    AUTH0_ROLES_CLAIM: str = ""
    AUTH0_PERMISSIONS_CLAIM: str = ""

    model_config = SettingsConfigDict(extra="ignore", env_prefix="TENON_")

    @property
    def issuer(self) -> str:
        issuer = (self.AUTH0_ISSUER or f"https://{self.AUTH0_DOMAIN}/").strip()
        if issuer and not issuer.endswith("/"):
            issuer = f"{issuer}/"
        return issuer

    @property
    def jwks_url(self) -> str:
        return self.AUTH0_JWKS_URL or f"https://{self.AUTH0_DOMAIN}/.well-known/jwks.json"

    @property
    def audience(self) -> str:
        return self.AUTH0_API_AUDIENCE

    @property
    def algorithms(self) -> list[str]:
        parts = [part.strip() for part in self.AUTH0_ALGORITHMS.split(",") if part.strip()]
        return parts or ["RS256"]

    @model_validator(mode="after")
    def _apply_claim_namespace(self):
        namespace = claim_namespace(self.AUTH0_CLAIM_NAMESPACE)
        if not self.AUTH0_EMAIL_CLAIM:
            self.AUTH0_EMAIL_CLAIM = claim_uri(namespace, "email")
        if not self.AUTH0_ROLES_CLAIM:
            self.AUTH0_ROLES_CLAIM = claim_uri(namespace, "roles")
        if not self.AUTH0_PERMISSIONS_CLAIM:
            self.AUTH0_PERMISSIONS_CLAIM = claim_uri(namespace, "permissions")
        return self

    @property
    def permissions_str_claim(self) -> str:
        return claim_uri(self.AUTH0_CLAIM_NAMESPACE, "permissions_str")

    @property
    def name_claim(self) -> str:
        return claim_uri(self.AUTH0_CLAIM_NAMESPACE, "name")
