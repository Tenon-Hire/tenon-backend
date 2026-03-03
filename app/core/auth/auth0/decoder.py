from __future__ import annotations

import logging
from typing import Any

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from app.core.settings import settings

from .errors import Auth0Error

logger = logging.getLogger(__name__)


def _log_failure(reason: str, *, kid: str | None, alg: str | None) -> None:
    logger.warning(
        "auth0_token_validation_failed",
        extra={
            "reason": reason,
            "kid": kid,
            "alg": alg,
            "iss": settings.auth.issuer,
            "aud": settings.auth.audience,
        },
    )


def decode_auth0_token(token: str) -> dict[str, Any]:
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        _log_failure("invalid_token_header", kid=None, alg=None)
        raise Auth0Error("Invalid token header") from exc
    kid = unverified_header.get("kid")
    if kid is None:
        _log_failure("kid_missing", kid=None, alg=unverified_header.get("alg"))
        raise Auth0Error("Token header missing kid")
    alg = unverified_header.get("alg")
    if isinstance(alg, str) and alg.lower() == "none":
        _log_failure("invalid_algorithm", kid=kid, alg=alg)
        raise Auth0Error("Invalid token algorithm")

    allowed_algs = [a for a in settings.auth.algorithms if a.lower() != "none"]
    if not alg or alg not in allowed_algs:
        _log_failure("invalid_algorithm", kid=kid, alg=alg)
        raise Auth0Error("Invalid token algorithm")
    from app.core.auth import auth0

    jwks = auth0.get_jwks()
    key = next((jwk for jwk in jwks.get("keys", []) if jwk.get("kid") == kid), None)
    if key is None:
        auth0.clear_jwks_cache()
        jwks = auth0.get_jwks()
        key = next((jwk for jwk in jwks.get("keys", []) if jwk.get("kid") == kid), None)
        if key is None:
            _log_failure("kid_not_found", kid=kid, alg=alg)
            raise Auth0Error("Signing key not found")
    try:
        return jwt.decode(
            token,
            key,
            algorithms=allowed_algs,
            audience=settings.auth.audience,
            issuer=settings.auth.issuer,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
                "verify_nbf": True,
                "require_exp": True,
                "verify_at_hash": False,
                "leeway": settings.auth.AUTH0_LEEWAY_SECONDS,
            },
        )
    except ExpiredSignatureError as exc:
        _log_failure("expired", kid=kid, alg=alg)
        raise Auth0Error("Token expired") from exc
    except JWTError as exc:
        detail = str(exc).lower()
        if "audience" in detail:
            _log_failure("wrong_audience", kid=kid, alg=alg)
            raise Auth0Error("Invalid audience") from exc
        if "issuer" in detail:
            _log_failure("wrong_issuer", kid=kid, alg=alg)
            raise Auth0Error("Invalid issuer") from exc
        if "nbf" in detail:
            _log_failure("not_before_invalid", kid=kid, alg=alg)
            raise Auth0Error("Invalid not-before claim") from exc
        if "signature" in detail:
            _log_failure("invalid_signature", kid=kid, alg=alg)
            raise Auth0Error("Invalid signature") from exc
        _log_failure("invalid_token", kid=kid, alg=alg)
        raise Auth0Error("Invalid token") from exc


__all__ = ["decode_auth0_token", "_log_failure"]
