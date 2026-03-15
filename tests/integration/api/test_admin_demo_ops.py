from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.settings import settings
from app.domains import (
    AdminActionAudit,
    CandidateSession,
    Company,
    EvaluationRun,
    Job,
    ScenarioVersion,
    Simulation,
)
from app.jobs import worker
from app.repositories.evaluations.models import EVALUATION_RUN_STATUS_COMPLETED
from app.repositories.jobs.models import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCEEDED,
)
from tests.factories import (
    create_candidate_session,
    create_job,
    create_recruiter,
    create_simulation,
)


def _admin_headers(email: str = "demo-admin@test.com") -> dict[str, str]:
    return {"Authorization": f"Bearer recruiter:{email}"}


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
    monkeypatch.setattr(settings, "DEMO_ADMIN_ALLOWLIST_RECRUITER_IDS", [])
    monkeypatch.setattr(settings, "DEMO_ADMIN_JOB_STALE_SECONDS", 900)


@pytest.mark.asyncio
async def test_admin_demo_ops_hidden_when_demo_mode_disabled(async_client, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    response = await async_client.post(
        "/api/admin/jobs/job-123/requeue",
        json={"reason": "requeue for demo", "force": False},
        headers=_admin_headers(),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_demo_ops_hidden_without_auth_when_demo_mode_disabled(
    async_client, monkeypatch
):
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    response = await async_client.post(
        "/api/admin/jobs/job-123/requeue",
        json={"reason": "requeue for demo", "force": False},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_demo_ops_require_admin_when_demo_mode_enabled(
    async_client, monkeypatch
):
    _enable_demo_mode(monkeypatch, allowlist_emails=[])
    response = await async_client.post(
        "/api/admin/jobs/job-123/requeue",
        json={"reason": "requeue for demo", "force": False},
        headers=_admin_headers("not-allowlisted@test.com"),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_reset_candidate_session_writes_audit(
    async_client,
    async_session,
    monkeypatch,
):
    admin_email = "ops-reset@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    recruiter = await create_recruiter(async_session, email="owner-reset@test.com")
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    now = datetime.now(UTC).replace(microsecond=0)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="completed",
        candidate_auth0_sub="auth0|candidate-reset",
        claimed_at=now - timedelta(days=1),
        started_at=now - timedelta(hours=8),
        completed_at=now - timedelta(hours=1),
        with_default_schedule=True,
    )
    await async_session.commit()

    response = await async_client.post(
        f"/api/admin/candidate_sessions/{candidate_session.id}/reset",
        json={
            "targetState": "claimed",
            "reason": "Demo reset after wedged session",
            "overrideIfEvaluated": False,
            "dryRun": False,
        },
        headers=_admin_headers(admin_email),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["candidateSessionId"] == candidate_session.id
    assert payload["status"] == "ok"
    assert payload["resetTo"] == "claimed"
    assert isinstance(payload["auditId"], str) and payload["auditId"]

    refreshed = await async_session.get(type(candidate_session), candidate_session.id)
    assert refreshed is not None
    assert refreshed.status == "not_started"
    assert refreshed.claimed_at is not None
    assert refreshed.started_at is None
    assert refreshed.completed_at is None
    assert refreshed.scheduled_start_at is None
    assert refreshed.schedule_locked_at is None

    audit = await async_session.get(AdminActionAudit, payload["auditId"])
    assert audit is not None
    assert audit.action == "candidate_session_reset"
    assert audit.target_type == "candidate_session"
    assert audit.target_id == str(candidate_session.id)


@pytest.mark.asyncio
async def test_reset_candidate_session_blocks_evaluated_without_override(
    async_client,
    async_session,
    monkeypatch,
):
    admin_email = "ops-reset-eval@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    recruiter = await create_recruiter(async_session, email="owner-reset-eval@test.com")
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="completed",
        candidate_auth0_sub="auth0|candidate-eval",
        claimed_at=datetime.now(UTC) - timedelta(days=2),
    )
    evaluation_run = EvaluationRun(
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        status=EVALUATION_RUN_STATUS_COMPLETED,
        started_at=datetime.now(UTC) - timedelta(hours=2),
        completed_at=datetime.now(UTC) - timedelta(hours=1),
        model_name="eval-model",
        model_version="v1",
        prompt_version="p1",
        rubric_version="r1",
        day2_checkpoint_sha="day2sha",
        day3_final_sha="day3sha",
        cutoff_commit_sha="cutoffsha",
        transcript_reference="transcript://test",
    )
    async_session.add(evaluation_run)
    await async_session.commit()

    blocked = await async_client.post(
        f"/api/admin/candidate_sessions/{candidate_session.id}/reset",
        json={
            "targetState": "claimed",
            "reason": "Reset evaluated session",
            "overrideIfEvaluated": False,
            "dryRun": False,
        },
        headers=_admin_headers(admin_email),
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["errorCode"] == "UNSAFE_OPERATION"

    allowed = await async_client.post(
        f"/api/admin/candidate_sessions/{candidate_session.id}/reset",
        json={
            "targetState": "claimed",
            "reason": "Override evaluated reset for demo",
            "overrideIfEvaluated": True,
            "dryRun": False,
        },
        headers=_admin_headers(admin_email),
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_reset_candidate_session_dry_run_is_non_mutating(
    async_client,
    async_session,
    monkeypatch,
):
    admin_email = "ops-reset-dry-run@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    recruiter = await create_recruiter(async_session, email="owner-reset-dry@test.com")
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        candidate_auth0_sub="auth0|candidate-dry",
        claimed_at=datetime.now(UTC) - timedelta(days=1),
        started_at=datetime.now(UTC) - timedelta(hours=6),
    )
    candidate_session_id = candidate_session.id
    await async_session.commit()

    response = await async_client.post(
        f"/api/admin/candidate_sessions/{candidate_session.id}/reset",
        json={
            "targetState": "not_started",
            "reason": "Dry run reset",
            "overrideIfEvaluated": False,
            "dryRun": True,
        },
        headers=_admin_headers(admin_email),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "dry_run"
    assert payload["auditId"] is None

    await async_session.rollback()
    refreshed = await async_session.get(CandidateSession, candidate_session_id)
    assert refreshed is not None
    assert refreshed.status == "in_progress"
    assert refreshed.started_at is not None

    audits = (
        (
            await async_session.execute(
                select(AdminActionAudit).where(
                    AdminActionAudit.target_id == str(candidate_session.id),
                    AdminActionAudit.action == "candidate_session_reset",
                )
            )
        )
        .scalars()
        .all()
    )
    assert audits == []


@pytest.mark.asyncio
async def test_requeue_job_transitions_and_worker_processes(
    async_client,
    async_session,
    monkeypatch,
):
    admin_email = "ops-requeue@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    recruiter = await create_recruiter(async_session, email="owner-requeue@test.com")
    company = await async_session.get(Company, recruiter.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        job_type="admin_requeue_integration_job",
        status=JOB_STATUS_DEAD_LETTER,
        last_error="failed before demo",
        payload_json={"ok": True},
    )
    job_id = job.id
    await async_session.commit()

    response = await async_client.post(
        f"/api/admin/jobs/{job_id}/requeue",
        json={"reason": "Retry dead-lettered demo job", "force": False},
        headers=_admin_headers(admin_email),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["jobId"] == job_id
    assert body["previousStatus"] == JOB_STATUS_DEAD_LETTER
    assert body["newStatus"] == JOB_STATUS_QUEUED
    assert isinstance(body["auditId"], str)

    session_maker = _session_maker(async_session)
    worker.clear_handlers()
    try:
        worker.register_handler(
            "admin_requeue_integration_job", lambda _payload: {"ok": True}
        )
        handled = await worker.run_once(
            session_maker=session_maker,
            worker_id="admin-demo-ops-test-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True

    async_session.expire_all()
    refreshed_job = await async_session.get(Job, job_id)
    assert refreshed_job is not None
    assert refreshed_job.status == JOB_STATUS_SUCCEEDED


@pytest.mark.asyncio
async def test_requeue_queued_job_is_idempotent_noop(
    async_client,
    async_session,
    monkeypatch,
):
    admin_email = "ops-requeue-noop@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    recruiter = await create_recruiter(
        async_session, email="owner-requeue-noop@test.com"
    )
    company = await async_session.get(Company, recruiter.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_QUEUED,
        job_type="noop_requeue_job",
    )
    await async_session.commit()

    first = await async_client.post(
        f"/api/admin/jobs/{job.id}/requeue",
        json={"reason": "No-op check one", "force": False},
        headers=_admin_headers(admin_email),
    )
    assert first.status_code == 200, first.text
    assert first.json()["previousStatus"] == JOB_STATUS_QUEUED
    assert first.json()["newStatus"] == JOB_STATUS_QUEUED

    second = await async_client.post(
        f"/api/admin/jobs/{job.id}/requeue",
        json={"reason": "No-op check two", "force": False},
        headers=_admin_headers(admin_email),
    )
    assert second.status_code == 200, second.text
    assert second.json()["previousStatus"] == JOB_STATUS_QUEUED
    assert second.json()["newStatus"] == JOB_STATUS_QUEUED

    refreshed_job = await async_session.get(type(job), job.id)
    assert refreshed_job is not None
    assert refreshed_job.status == JOB_STATUS_QUEUED


@pytest.mark.asyncio
async def test_requeue_running_job_requires_force_if_not_stale(
    async_client,
    async_session,
    monkeypatch,
):
    admin_email = "ops-requeue-force@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    recruiter = await create_recruiter(
        async_session, email="owner-requeue-force@test.com"
    )
    company = await async_session.get(Company, recruiter.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_RUNNING,
        job_type="running_force_job",
        next_run_at=datetime.now(UTC),
    )
    job.locked_at = datetime.now(UTC)
    job.locked_by = "worker-1"
    await async_session.commit()

    blocked = await async_client.post(
        f"/api/admin/jobs/{job.id}/requeue",
        json={"reason": "Should block while fresh running", "force": False},
        headers=_admin_headers(admin_email),
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["errorCode"] == "UNSAFE_OPERATION"

    forced = await async_client.post(
        f"/api/admin/jobs/{job.id}/requeue",
        json={"reason": "Force requeue during demo", "force": True},
        headers=_admin_headers(admin_email),
    )
    assert forced.status_code == 200, forced.text
    assert forced.json()["newStatus"] == JOB_STATUS_QUEUED


@pytest.mark.asyncio
async def test_simulation_fallback_updates_future_invites_only(
    async_client,
    async_session,
    monkeypatch,
    auth_header_factory,
):
    admin_email = "ops-fallback@test.com"
    _enable_demo_mode(monkeypatch, allowlist_emails=[admin_email])

    recruiter = await create_recruiter(async_session, email="owner-fallback@test.com")
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    first_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        invite_email="first-fallback@example.com",
    )

    scenario_v1 = await async_session.get(
        ScenarioVersion, simulation.active_scenario_version_id
    )
    assert scenario_v1 is not None
    scenario_v2 = ScenarioVersion(
        simulation_id=simulation.id,
        version_index=2,
        status="ready",
        storyline_md=f"{scenario_v1.storyline_md}\n\nFallback variant",
        task_prompts_json=scenario_v1.task_prompts_json,
        rubric_json=scenario_v1.rubric_json,
        focus_notes=scenario_v1.focus_notes,
        template_key=scenario_v1.template_key,
        tech_stack=scenario_v1.tech_stack,
        seniority=scenario_v1.seniority,
    )
    async_session.add(scenario_v2)
    await async_session.commit()

    fallback_response = await async_client.post(
        f"/api/admin/simulations/{simulation.id}/scenario/use_fallback",
        json={
            "scenarioVersionId": scenario_v2.id,
            "applyTo": "future_invites_only",
            "reason": "Swap to known-good fallback for demo",
            "dryRun": False,
        },
        headers=_admin_headers(admin_email),
    )
    assert fallback_response.status_code == 200, fallback_response.text
    fallback_payload = fallback_response.json()
    assert fallback_payload["simulationId"] == simulation.id
    assert fallback_payload["activeScenarioVersionId"] == scenario_v2.id
    assert fallback_payload["applyTo"] == "future_invites_only"
    assert isinstance(fallback_payload["auditId"], str)

    refreshed_simulation = await async_session.get(Simulation, simulation.id)
    assert refreshed_simulation is not None
    assert refreshed_simulation.active_scenario_version_id == scenario_v2.id

    refreshed_first = await async_session.get(type(first_session), first_session.id)
    assert refreshed_first is not None
    assert refreshed_first.scenario_version_id == scenario_v1.id

    invite_response = await async_client.post(
        f"/api/simulations/{simulation.id}/invite",
        headers=auth_header_factory(recruiter),
        json={
            "candidateName": "Second Candidate",
            "inviteEmail": "second-fallback@example.com",
        },
    )
    assert invite_response.status_code == 200, invite_response.text
    second_session_id = invite_response.json()["candidateSessionId"]
    second_session = await async_session.get(type(first_session), second_session_id)
    assert second_session is not None
    assert second_session.scenario_version_id == scenario_v2.id

    noop_response = await async_client.post(
        f"/api/admin/simulations/{simulation.id}/scenario/use_fallback",
        json={
            "scenarioVersionId": scenario_v2.id,
            "applyTo": "future_invites_only",
            "reason": "Repeat fallback no-op",
            "dryRun": False,
        },
        headers=_admin_headers(admin_email),
    )
    assert noop_response.status_code == 200, noop_response.text
    assert noop_response.json()["activeScenarioVersionId"] == scenario_v2.id

    audit = await async_session.get(AdminActionAudit, fallback_payload["auditId"])
    assert audit is not None
    assert audit.action == "simulation_use_fallback"
    assert audit.target_type == "simulation"
    assert audit.target_id == str(simulation.id)
