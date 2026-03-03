from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.env import env_name

from .bearer import bearer_scheme
from .builder import build_principal
from .dev_principal import build_dev_principal, parse_dev_principal_token
from .model import Principal
from .token_decoder import decode_credentials

logger = logging.getLogger(__name__)


async def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    request: Request,
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    request_id = (
        request.headers.get("x-request-id")
        or request.headers.get("x-correlation-id")
        or ""
    ).strip() or None

    # Reject shorthand/dev bearer tokens outside test to prevent auth bypass.
    if (
        parse_dev_principal_token(credentials.credentials or "")
        and env_name() != "test"
    ):
        logger.warning(
            "auth_token_rejected",
            extra={
                "request_id": request_id,
                "reason": "bypass_blocked",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    dev_principal = build_dev_principal(credentials)
    if dev_principal:
        return dev_principal

    claims = decode_credentials(credentials, request_id)
    try:
        return build_principal(claims)
    except HTTPException as exc:
        logger.warning(
            "auth0_claims_invalid",
            extra={
                "request_id": request_id,
                "detail": exc.detail,
                "reason": "claims_invalid",
            },
        )
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            ) from exc
        raise
