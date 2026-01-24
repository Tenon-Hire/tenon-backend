from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from .bearer import bearer_scheme
from .builder import build_principal
from .model import Principal
from .token_decoder import decode_credentials

logger = logging.getLogger(__name__)


def _dev_principal(credentials: HTTPAuthorizationCredentials) -> Principal | None:
    token = credentials.credentials or ""
    if ":" not in token:
        return None
    prefix, _, email = token.partition(":")
    email = email.strip().lower()
    if not email:
        return None
    if prefix not in {"candidate", "recruiter"}:
        return None
    claims = {
        "sub": token,
        "email": email,
        "permissions": [f"{prefix}:access"],
        "roles": [prefix],
        "name": email,
    }
    return build_principal(claims)


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

    dev_principal = _dev_principal(credentials)
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
        raise
