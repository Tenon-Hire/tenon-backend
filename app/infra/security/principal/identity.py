from __future__ import annotations

import logging

from fastapi import HTTPException, status

from app.infra.config import settings

from .selectors import first_claim, normalize_email

logger = logging.getLogger(__name__)


def extract_identity(claims: dict[str, object]) -> tuple[str, str, str | None, list[str]]:
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    configured_email_claim = (settings.auth.AUTH0_EMAIL_CLAIM or "").strip()
    if not configured_email_claim:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AUTH0_EMAIL_CLAIM not configured"
        )

    email = normalize_email(
        first_claim(
            claims,
            [
                configured_email_claim,
                "email",
                next((k for k in claims if isinstance(k, str) and k.endswith("/email")), None),
            ],
            default=None,
        )
    )
    if not email:
        try:
            available_claim_keys = sorted([str(k) for k in claims])[:50]
        except Exception:  # pragma: no cover - defensive
            available_claim_keys = []
        logger.debug(
            "email_claim_missing",
            extra={
                "expected_email_claim": configured_email_claim,
                "available_claim_keys": available_claim_keys,
            },
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    name_raw = first_claim(claims, ["name", settings.auth.name_claim], default=None)
    name = name_raw.strip() if isinstance(name_raw, str) and name_raw.strip() else None
    roles_claim = first_claim(claims, [settings.auth.AUTH0_ROLES_CLAIM, "roles"], default=[])
    roles = [r for r in roles_claim or [] if isinstance(r, str)]
    return sub, email, name, roles
