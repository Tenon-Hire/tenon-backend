"""Application module for auth principal dev principal utils workflows."""

from __future__ import annotations

from fastapi.security import HTTPAuthorizationCredentials

from app.shared.utils.shared_utils_env_utils import env_name

from .shared_auth_principal_builder_utils import build_principal
from .shared_auth_principal_model import Principal


def parse_dev_principal_token(token: str) -> tuple[str, str] | None:
    """Parse dev principal token."""
    if ":" not in token:
        return None
    prefix, _, email = token.partition(":")
    email = email.strip().lower()
    if not email or prefix not in {"candidate", "recruiter"}:
        return None
    return prefix, email


def build_dev_principal(credentials: HTTPAuthorizationCredentials) -> Principal | None:
    # Dev shorthand principals are strictly test-only.
    """Build dev principal."""
    if env_name() != "test":
        return None

    parsed = parse_dev_principal_token(credentials.credentials or "")
    if parsed is None:
        return None
    prefix, email = parsed

    claims = {
        "sub": f"{prefix}:{email}",
        "email": email,
        "permissions": [f"{prefix}:access"],
        "roles": [prefix],
        "name": email,
    }
    return build_principal(claims)


__all__ = ["build_dev_principal", "parse_dev_principal_token"]
