from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.auth.principal import Principal
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
)
from tests.shared.factories import (
    create_candidate_session,
    create_company,
    create_job,
    create_talent_partner,
    create_trial,
)


def _principal(
    email: str,
    permissions: list[str],
    *,
    sub: str | None = None,
    email_verified: bool | None = None,
) -> Principal:
    claims: dict[str, object] = {}
    if email_verified is not None:
        claims["email_verified"] = email_verified
    return Principal(
        sub=sub or f"principal-{email}",
        email=email,
        name=email.split("@")[0],
        roles=[],
        permissions=permissions,
        claims=claims,
    )


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )


__all__ = [name for name in globals() if not name.startswith("__")]
