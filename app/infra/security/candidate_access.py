from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.candidate_sessions import repository as cs_repo
from app.domains.candidate_sessions.auth_tokens import hash_token
from app.infra.config import settings
from app.infra.db import get_session
from app.infra.security.principal import Principal, bearer_scheme


def _is_expired(dt: datetime | None, *, now: datetime) -> bool:
    if dt is None:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt < now


def _is_candidate_token(token: str) -> bool:
    return token.count(".") == 2


def _decode_candidate_token(token: str) -> dict | None:
    try:
        claims = jwt.get_unverified_claims(token)
    except JWTError:
        return None
    if claims.get("typ") != "candidate":
        return None
    return jwt.decode(
        token,
        settings.auth.CANDIDATE_TOKEN_SECRET,
        algorithms=[settings.auth.CANDIDATE_TOKEN_ALGORITHM],
        options={"verify_aud": False},
    )


async def require_candidate_principal(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Principal:
    """Require a verified candidate access token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    token = credentials.credentials or ""
    now = datetime.now(UTC)

    if not _is_candidate_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        claims = _decode_candidate_token(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    sub = claims.get("sub")
    invite_email = (claims.get("invite_email") or "").strip().lower()
    if not sub or not invite_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    try:
        session_id = int(sub)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc

    cs = await cs_repo.get_by_id(db, session_id)
    if cs is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    if invite_email != (cs.invite_email or "").strip().lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    token_hash = hash_token(token)
    if cs.candidate_access_token_hash != token_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    if _is_expired(getattr(cs, "candidate_access_token_expires_at", None), now=now):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )

    return Principal(
        sub=str(session_id),
        email=invite_email,
        name=cs.candidate_name or (invite_email.split("@")[0]),
        roles=[],
        permissions=["candidate:access"],
        claims={
            "sub": str(session_id),
            "invite_email": invite_email,
            "typ": "candidate",
            "email": invite_email,
            settings.auth.AUTH0_EMAIL_CLAIM: invite_email,
            "permissions": ["candidate:access"],
            settings.auth.AUTH0_PERMISSIONS_CLAIM: ["candidate:access"],
            "candidate_session_id": session_id,
        },
    )
