from datetime import UTC, datetime, timedelta

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.domains.candidate_sessions.auth_tokens import hash_token, mint_candidate_token
from app.infra.config import settings
from app.infra.security import candidate_access
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def test_is_candidate_token():
    assert candidate_access._is_candidate_token("a.b.c") is True
    assert candidate_access._is_candidate_token("abc") is False


def test_decode_candidate_token_typ_mismatch():
    token = jwt.encode(
        {"typ": "other"},
        settings.auth.CANDIDATE_TOKEN_SECRET,
        algorithm=settings.auth.CANDIDATE_TOKEN_ALGORITHM,
    )
    assert candidate_access._decode_candidate_token(token) is None


def test_is_expired_variants():
    now = datetime.now(UTC)
    assert candidate_access._is_expired(None, now=now) is True
    assert candidate_access._is_expired(now - timedelta(minutes=1), now=now) is True
    assert candidate_access._is_expired(now + timedelta(minutes=1), now=now) is False


def test_is_expired_with_naive_datetime():
    now = datetime.now(UTC)
    naive = datetime.utcnow() - timedelta(minutes=1)
    assert candidate_access._is_expired(naive, now=now) is True


@pytest.mark.asyncio
async def test_require_candidate_principal_success(async_session):
    recruiter = await create_recruiter(async_session, email="candidate@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)
    token, token_hash, expires_at, issued_at = mint_candidate_token(
        candidate_session_id=cs.id,
        invite_email=cs.invite_email,
        now=datetime.now(UTC),
    )
    cs.candidate_access_token_hash = token_hash
    cs.candidate_access_token_expires_at = expires_at
    cs.candidate_access_token_issued_at = issued_at
    await async_session.commit()

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )
    principal = await candidate_access.require_candidate_principal(
        credentials, async_session
    )
    assert principal.sub == str(cs.id)
    assert principal.email == cs.invite_email


@pytest.mark.asyncio
async def test_require_candidate_principal_invalid_hash(async_session):
    recruiter = await create_recruiter(async_session, email="hash@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)
    token, _, expires_at, issued_at = mint_candidate_token(
        candidate_session_id=cs.id,
        invite_email=cs.invite_email,
        now=datetime.now(UTC),
    )
    cs.candidate_access_token_hash = hash_token("different")
    cs.candidate_access_token_expires_at = expires_at
    cs.candidate_access_token_issued_at = issued_at
    await async_session.commit()

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )
    with pytest.raises(Exception) as excinfo:
        await candidate_access.require_candidate_principal(credentials, async_session)
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_require_candidate_principal_missing_credentials(async_session):
    with pytest.raises(Exception) as excinfo:
        await candidate_access.require_candidate_principal(None, async_session)
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_require_candidate_principal_invalid_token_format(async_session):
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="not-a-jwt",
    )
    with pytest.raises(Exception) as excinfo:
        await candidate_access.require_candidate_principal(credentials, async_session)
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_require_candidate_principal_decode_failure(async_session):
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="a.b.c",
    )
    with pytest.raises(Exception) as excinfo:
        await candidate_access.require_candidate_principal(credentials, async_session)
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_require_candidate_principal_missing_claims(async_session):
    token = jwt.encode(
        {"typ": "candidate"},
        settings.auth.CANDIDATE_TOKEN_SECRET,
        algorithm=settings.auth.CANDIDATE_TOKEN_ALGORITHM,
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )
    with pytest.raises(Exception) as excinfo:
        await candidate_access.require_candidate_principal(credentials, async_session)
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_require_candidate_principal_invalid_sub(async_session):
    token = jwt.encode(
        {"typ": "candidate", "sub": "not-an-int", "invite_email": "a@test.com"},
        settings.auth.CANDIDATE_TOKEN_SECRET,
        algorithm=settings.auth.CANDIDATE_TOKEN_ALGORITHM,
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )
    with pytest.raises(Exception) as excinfo:
        await candidate_access.require_candidate_principal(credentials, async_session)
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_require_candidate_principal_missing_session(async_session):
    token = jwt.encode(
        {"typ": "candidate", "sub": "999", "invite_email": "a@test.com"},
        settings.auth.CANDIDATE_TOKEN_SECRET,
        algorithm=settings.auth.CANDIDATE_TOKEN_ALGORITHM,
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )
    with pytest.raises(Exception) as excinfo:
        await candidate_access.require_candidate_principal(credentials, async_session)
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_require_candidate_principal_invite_email_mismatch(async_session):
    recruiter = await create_recruiter(async_session, email="mismatch@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)
    token = jwt.encode(
        {"typ": "candidate", "sub": str(cs.id), "invite_email": "other@test.com"},
        settings.auth.CANDIDATE_TOKEN_SECRET,
        algorithm=settings.auth.CANDIDATE_TOKEN_ALGORITHM,
    )
    cs.candidate_access_token_hash = hash_token(token)
    cs.candidate_access_token_expires_at = datetime.now(UTC) + timedelta(minutes=5)
    await async_session.commit()

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )
    with pytest.raises(Exception) as excinfo:
        await candidate_access.require_candidate_principal(credentials, async_session)
    assert excinfo.value.status_code == 403


@pytest.mark.asyncio
async def test_require_candidate_principal_expired(async_session):
    recruiter = await create_recruiter(async_session, email="expired@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)
    token, token_hash, _, issued_at = mint_candidate_token(
        candidate_session_id=cs.id,
        invite_email=cs.invite_email,
        now=datetime.now(UTC),
    )
    cs.candidate_access_token_hash = token_hash
    cs.candidate_access_token_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    cs.candidate_access_token_issued_at = issued_at
    await async_session.commit()

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )
    with pytest.raises(Exception) as excinfo:
        await candidate_access.require_candidate_principal(credentials, async_session)
    assert excinfo.value.status_code == 401
