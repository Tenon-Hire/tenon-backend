from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.auth.principal import Principal
from app.repositories.jobs import repository as jobs_repo
from app.repositories.jobs.models import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
)
from tests.factories import (
    create_candidate_session,
    create_company,
    create_job,
    create_recruiter,
    create_simulation,
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


@pytest.mark.asyncio
async def test_create_or_get_idempotent_returns_existing(async_session):
    company = await create_company(async_session, name="Jobs Co")

    first = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-1",
        payload_json={"a": 1},
        company_id=company.id,
    )
    second = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-1",
        payload_json={"a": 2},
        company_id=company.id,
    )

    assert first.id == second.id
    fetched = await jobs_repo.get_by_id(async_session, first.id)
    assert fetched is not None
    assert fetched.id == first.id


@pytest.mark.asyncio
async def test_claim_next_runnable_prevents_double_claim_with_two_sessions(
    async_session,
):
    company = await create_company(async_session, name="Jobs Co Double Claim")
    job = await create_job(
        async_session,
        company=company,
        status="queued",
        attempt=0,
        next_run_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    await async_session.commit()

    session_maker = _session_maker(async_session)
    now = datetime.now(UTC)
    async with session_maker() as session_a, session_maker() as session_b:
        claimed_a, claimed_b = await asyncio.gather(
            jobs_repo.claim_next_runnable(
                session_a,
                worker_id="worker-a",
                now=now,
                lease_seconds=300,
            ),
            jobs_repo.claim_next_runnable(
                session_b,
                worker_id="worker-b",
                now=now,
                lease_seconds=300,
            ),
        )

    claimed = [job_row for job_row in [claimed_a, claimed_b] if job_row is not None]
    assert len(claimed) == 1
    winning_claim = claimed[0]
    assert winning_claim.id == job.id
    assert winning_claim.status == JOB_STATUS_RUNNING
    assert winning_claim.attempt == 1
    assert winning_claim.locked_by in {"worker-a", "worker-b"}

    refreshed = await jobs_repo.get_by_id(async_session, job.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_RUNNING
    assert refreshed.locked_by == winning_claim.locked_by


@pytest.mark.asyncio
async def test_claim_next_runnable_never_reclaims_terminal_state_jobs(async_session):
    company = await create_company(async_session, name="Jobs Co Terminal")
    old_lock = datetime.now(UTC) - timedelta(hours=4)
    succeeded = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_SUCCEEDED,
        attempt=3,
        max_attempts=5,
        next_run_at=None,
    )
    succeeded.locked_at = old_lock
    succeeded.locked_by = "old-worker-succeeded"

    dead_letter = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_DEAD_LETTER,
        attempt=5,
        max_attempts=5,
        next_run_at=None,
    )
    dead_letter.locked_at = old_lock
    dead_letter.locked_by = "old-worker-dead-letter"
    await async_session.commit()

    claimed = await jobs_repo.claim_next_runnable(
        async_session,
        worker_id="fresh-worker",
        now=datetime.now(UTC),
        lease_seconds=300,
    )
    assert claimed is None

    refreshed_succeeded = await jobs_repo.get_by_id(async_session, succeeded.id)
    refreshed_dead_letter = await jobs_repo.get_by_id(async_session, dead_letter.id)
    assert refreshed_succeeded is not None
    assert refreshed_dead_letter is not None
    assert refreshed_succeeded.status == JOB_STATUS_SUCCEEDED
    assert refreshed_dead_letter.status == JOB_STATUS_DEAD_LETTER


@pytest.mark.asyncio
async def test_create_or_get_idempotent_validates_payload_and_inputs(async_session):
    company = await create_company(async_session, name="Jobs Co 2")
    with pytest.raises(ValueError):
        await jobs_repo.create_or_get_idempotent(
            async_session,
            job_type=" ",
            idempotency_key="idem-2",
            payload_json={"ok": True},
            company_id=company.id,
        )
    with pytest.raises(ValueError):
        await jobs_repo.create_or_get_idempotent(
            async_session,
            job_type="x",
            idempotency_key=" ",
            payload_json={"ok": True},
            company_id=company.id,
        )
    with pytest.raises(ValueError):
        await jobs_repo.create_or_get_idempotent(
            async_session,
            job_type="x",
            idempotency_key="idem-2",
            payload_json={"ok": True},
            company_id=company.id,
            max_attempts=0,
        )
    with pytest.raises(ValueError):
        await jobs_repo.create_or_get_idempotent(
            async_session,
            job_type="x",
            idempotency_key="idem-3",
            payload_json={"blob": "x" * (jobs_repo.MAX_JOB_PAYLOAD_BYTES + 1)},
            company_id=company.id,
        )


@pytest.mark.asyncio
async def test_mark_failed_and_reschedule_sanitizes_and_truncates_last_error(
    async_session,
):
    company = await create_company(async_session, name="Jobs Co Error Hygiene")
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-error-hygiene",
        payload_json={"ok": True},
        company_id=company.id,
    )

    now = datetime.now(UTC)
    raw_error = "RuntimeError:\n" + ("temporary\tfailure\n" * 600)
    await jobs_repo.mark_failed_and_reschedule(
        async_session,
        job_id=job.id,
        error_str=raw_error,
        next_run_at=now + timedelta(seconds=5),
        now=now,
    )

    refreshed = await jobs_repo.get_by_id(async_session, job.id)
    assert refreshed is not None
    assert refreshed.last_error is not None
    assert len(refreshed.last_error) <= jobs_repo.MAX_JOB_ERROR_CHARS
    assert "\n" not in refreshed.last_error
    assert "\r" not in refreshed.last_error


@pytest.mark.asyncio
async def test_claim_next_runnable_reclaims_stale_running_job(async_session):
    company = await create_company(async_session, name="Jobs Co 3")
    stale_time = datetime.now(UTC) - timedelta(minutes=20)
    running_job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_RUNNING,
        attempt=1,
        next_run_at=None,
    )
    running_job.locked_at = stale_time
    await async_session.commit()

    claimed = await jobs_repo.claim_next_runnable(
        async_session,
        worker_id="w1",
        now=datetime.now(UTC),
        lease_seconds=300,
    )
    assert claimed is not None
    assert claimed.id == running_job.id
    assert claimed.status == JOB_STATUS_RUNNING
    assert claimed.attempt == 2
    assert claimed.locked_by == "w1"


@pytest.mark.asyncio
async def test_get_by_id_for_principal_recruiter_and_candidate(async_session):
    recruiter = await create_recruiter(
        async_session, email="jobs-owner-lookup@test.com"
    )
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="jobs-candidate-lookup@test.com",
        candidate_auth0_sub="candidate-sub-1",
    )
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="transcript_processing",
        idempotency_key="idem-principal",
        payload_json={"candidateSessionId": cs.id},
        company_id=recruiter.company_id,
        candidate_session_id=cs.id,
    )

    recruiter_principal = _principal(recruiter.email, ["recruiter:access"])
    candidate_principal = _principal(
        "jobs-candidate-lookup@test.com",
        ["candidate:access"],
        sub="candidate-sub-1",
        email_verified=True,
    )
    unknown_principal = _principal(
        "nobody@test.com",
        ["candidate:access"],
        email_verified=True,
    )

    recruiter_view = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, recruiter_principal
    )
    candidate_view = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, candidate_principal
    )
    denied_view = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, unknown_principal
    )
    assert recruiter_view is not None
    assert candidate_view is not None
    assert denied_view is None


@pytest.mark.asyncio
async def test_get_by_id_for_principal_denies_candidate_when_claimed_by_other_sub(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="jobs-owner-sub-check@test.com"
    )
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="jobs-candidate-sub-check@test.com",
        candidate_auth0_sub="candidate-sub-owner",
    )
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="transcript_processing",
        idempotency_key="idem-sub-check",
        payload_json={"candidateSessionId": cs.id},
        company_id=recruiter.company_id,
        candidate_session_id=cs.id,
    )

    wrong_sub_principal = _principal(
        cs.invite_email,
        ["candidate:access"],
        sub="candidate-sub-attacker",
        email_verified=True,
    )
    denied = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, wrong_sub_principal
    )
    assert denied is None


@pytest.mark.asyncio
async def test_get_by_id_for_principal_denies_unverified_candidate(async_session):
    recruiter = await create_recruiter(
        async_session, email="jobs-owner-unverified@test.com"
    )
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="jobs-candidate-unverified@test.com",
    )
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="transcript_processing",
        idempotency_key="idem-unverified",
        payload_json={"candidateSessionId": cs.id},
        company_id=recruiter.company_id,
        candidate_session_id=cs.id,
    )

    unverified_principal = _principal(
        cs.invite_email,
        ["candidate:access"],
        sub="candidate-unverified",
        email_verified=False,
    )
    denied = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, unverified_principal
    )
    assert denied is None


@pytest.mark.asyncio
async def test_get_by_id_for_principal_denies_company_scoped_job_for_candidate(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="jobs-owner-company-scoped@test.com"
    )
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        invite_email="jobs-candidate-company-scoped@test.com",
    )
    job = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="scenario_generation",
        idempotency_key="idem-company-scoped",
        payload_json={"simulationId": sim.id},
        company_id=recruiter.company_id,
        candidate_session_id=None,
    )

    candidate_principal = _principal(
        cs.invite_email,
        ["candidate:access"],
        sub="candidate-company-scoped",
        email_verified=True,
    )
    denied = await jobs_repo.get_by_id_for_principal(
        async_session, job.id, candidate_principal
    )
    assert denied is None
