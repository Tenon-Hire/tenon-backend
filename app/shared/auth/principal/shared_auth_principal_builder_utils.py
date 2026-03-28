"""Application module for auth principal builder utils workflows."""

from __future__ import annotations

from .shared_auth_principal_identity_utils import extract_identity
from .shared_auth_principal_model import Principal
from .shared_auth_principal_permissions_utils import build_permissions


def build_principal(claims: dict) -> Principal:
    """Build principal."""
    sub, email, name, roles = extract_identity(claims)
    permissions = build_permissions(claims, roles)
    return Principal(
        sub=sub,
        email=email,
        name=name or email.split("@")[0],
        roles=roles,
        permissions=permissions,
        claims=claims,
    )
