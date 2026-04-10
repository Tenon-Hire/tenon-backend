from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.evaluations.repositories import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EvaluationRun,
)
from app.shared.database.shared_database_models_model import (
    AdminActionAudit,
    CandidateSession,
    Company,
    ScenarioVersion,
    Trial,
)
from app.shared.jobs import worker
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
    Job,
)
from tests.shared.factories import (
    create_candidate_session,
    create_job,
    create_talent_partner,
    create_trial,
)


def _admin_headers(email: str = "demo-admin@test.com") -> dict[str, str]:
    return {"Authorization": f"Bearer talent_partner:{email}"}


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )


def _enable_demo_mode(
    monkeypatch, *, allowlist_emails: list[str] | None = None
) -> None:
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_EMAILS", allowlist_emails or [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_SUBJECTS", [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_TALENT_PARTNER_IDS", [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_JOB_STALE_SECONDS", 900)


__all__ = [name for name in globals() if not name.startswith("__")]
