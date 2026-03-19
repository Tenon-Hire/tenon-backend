from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.core.env import env_name
from app.core.settings import settings

from .bearer import bearer_scheme
from .builder import build_principal
from .dev_principal import build_dev_principal, parse_dev_principal_token
from .model import Principal
from .token_decoder import decode_credentials

logger = logging.getLogger(__name__)


def _is_local_client(request: Request) -> bool:
    client_host = getattr(request.client, "host", "")
    return client_host in {"127.0.0.1", "::1", "localhost"}


async def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    request: Request,
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    token = (credentials.credentials or "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    credentials = HTTPAuthorizationCredentials(
        scheme=credentials.scheme, credentials=token
    )

    request_id = (
        request.headers.get("x-request-id")
        or request.headers.get("x-correlation-id")
        or ""
    ).strip() or None

    parsed_dev = parse_dev_principal_token(token)
    if parsed_dev:
        env = env_name()
        if env == "test":
            dev_principal = build_dev_principal(credentials)
            if dev_principal:
                return dev_principal
        elif (
            env == "local"
            and settings.dev_auth_bypass_enabled
            and _is_local_client(request)
        ):
            prefix, email = parsed_dev
            claims = {
                "sub": f"{prefix}:{email}",
                "email": email,
                "permissions": [f"{prefix}:access"],
                "roles": [prefix],
                "name": email,
            }
            return build_principal(claims)

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
