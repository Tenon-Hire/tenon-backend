"""Application module for auth principal checks utils workflows."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status

from .shared_auth_principal_dependencies_utils import get_principal
from .shared_auth_principal_model import Principal


def require_permissions(required: list[str]):
    """Dependency enforcing that the principal has all required permissions."""

    async def _dependency(
        principal: Annotated[Principal, Depends(get_principal)],
    ) -> Principal:
        missing = [p for p in required if p not in principal.permissions]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return principal

    return _dependency
