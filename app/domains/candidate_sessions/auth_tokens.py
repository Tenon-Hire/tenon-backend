from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from jose import jwt

from app.infra.config import settings

TOKEN_TTL_MINUTES = 60


def hash_token(token: str) -> str:
    """Return a hex digest for the candidate access token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def mint_candidate_token(
    *, candidate_session_id: int, invite_email: str, now: datetime | None = None
):
    """Generate a signed candidate access token and metadata."""
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    ttl_minutes = settings.auth.CANDIDATE_TOKEN_TTL_MINUTES or TOKEN_TTL_MINUTES
    expires_at = now + timedelta(minutes=ttl_minutes)
    claims = {
        "sub": str(candidate_session_id),
        "invite_email": invite_email,
        "typ": "candidate",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(
        claims,
        settings.auth.CANDIDATE_TOKEN_SECRET,
        algorithm=settings.auth.CANDIDATE_TOKEN_ALGORITHM,
    )
    token_hash = hash_token(token)
    return token, token_hash, expires_at, now
