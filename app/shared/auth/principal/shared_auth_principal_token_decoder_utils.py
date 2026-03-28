"""Application module for auth principal token decoder utils workflows."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.shared.auth import auth0

logger = logging.getLogger(__name__)


def decode_credentials(
    credentials: HTTPAuthorizationCredentials, request_id: str | None
) -> dict:
    """Execute decode credentials."""
    try:
        return auth0.decode_auth0_token(credentials.credentials)
    except auth0.Auth0Error as exc:
        reason = "invalid_token"
        detail_lower = str(exc.detail).lower()
        if detail_lower.startswith("invalid token header"):
            reason = "invalid_header"
        elif detail_lower.startswith("token header missing kid"):
            reason = "kid_missing"
        elif detail_lower.startswith("invalid token algorithm"):
            reason = "invalid_algorithm"
        elif exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            reason = "jwks_fetch_failed"
        elif detail_lower.startswith("token expired"):
            reason = "expired"
        elif detail_lower.startswith("signing key not found"):
            reason = "kid_not_found"
        elif "audience" in detail_lower:
            reason = "wrong_audience"
        elif "issuer" in detail_lower:
            reason = "wrong_issuer"
        elif "signature" in detail_lower:
            reason = "invalid_signature"
        logger.warning(
            "auth0_token_invalid",
            extra={"request_id": request_id, "reason": reason},
        )
        if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth provider unavailable",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        ) from exc
