from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.dependencies.admin_demo import DemoAdminActor
from app.core.auth.principal import Principal
from app.core.errors import ApiError
from app.core.settings import settings
from app.domains import (
    AdminActionAudit,
    Company,
    EvaluationRun,
    ScenarioVersion,
)
from app.repositories.evaluations.models import EVALUATION_RUN_STATUS_COMPLETED
from app.repositories.jobs.models import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
)
from app.repositories.scenario_versions.models import (
    SCENARIO_VERSION_STATUS_GENERATING,
    SCENARIO_VERSION_STATUS_READY,
)
from app.repositories.simulations.simulation import SIMULATION_STATUS_TERMINATED
from app.services import admin_ops_service
from tests.factories import (
    create_candidate_session,
    create_job,
    create_recruiter,
    create_simulation,
)


def _actor() -> DemoAdminActor:
    principal = Principal(
        sub="auth0|demo-admin",
        email="demo-admin@test.com",
        name="demo-admin",
        roles=["admin"],
        permissions=["recruiter:access"],
        claims={"sub": "auth0|demo-admin", "email": "demo-admin@test.com"},
    )
    return DemoAdminActor(
        principal=principal,
        actor_type="principal_admin",
        actor_id=principal.sub,
        recruiter_id=None,
    )


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def _create_scenario_version(
    async_session,
    *,
    simulation_id: int,
    version_index: int,
    status: str = SCENARIO_VERSION_STATUS_READY,
) -> ScenarioVersion:
    base = await async_session.get(
        ScenarioVersion,
        (
            await async_session.execute(
                select(ScenarioVersion.id)
                .where(ScenarioVersion.simulation_id == simulation_id)
                .order_by(ScenarioVersion.version_index.asc())
                .limit(1)
            )
        ).scalar_one(),
    )
    assert base is not None
    scenario_version = ScenarioVersion(
        simulation_id=simulation_id,
        version_index=version_index,
        status=status,
        storyline_md=f"{base.storyline_md}\n\nvariant-{version_index}",
        task_prompts_json=base.task_prompts_json,
        rubric_json=base.rubric_json,
        focus_notes=base.focus_notes,
        template_key=base.template_key,
        tech_stack=base.tech_stack,
        seniority=base.seniority,
    )
    async_session.add(scenario_version)
    await async_session.flush()
    return scenario_version


async def _audit_by_id(async_session, audit_id: str) -> AdminActionAudit:
    audit = await async_session.get(AdminActionAudit, audit_id)
    assert audit is not None
    return audit


@pytest.mark.asyncio
async def test_reset_candidate_session_dry_run_is_non_mutating(async_session):
    recruiter = await create_recruiter(async_session, email="reset-dry-owner@test.com")
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="in_progress",
        candidate_auth0_sub="auth0|candidate-reset-dry",
        candidate_email="candidate-reset-dry@test.com",
        started_at=datetime.now(UTC) - timedelta(hours=1),
        with_default_schedule=True,
    )
    candidate_session_id = candidate_session.id
    await async_session.commit()

    result = await admin_ops_service.reset_candidate_session(
        async_session,
        actor=_actor(),
        candidate_session_id=candidate_session_id,
        target_state="not_started",
        reason="  Demo   dry\nrun reset  ",
        override_if_evaluated=False,
        dry_run=True,
        now=datetime(2026, 1, 2, 10, 30, 0),
    )
    assert result.status == "dry_run"
    assert result.audit_id is None

    refreshed = await async_session.get(type(candidate_session), candidate_session_id)
    assert refreshed is not None
    assert refreshed.status == "in_progress"
    assert refreshed.candidate_auth0_sub == "auth0|candidate-reset-dry"
    assert refreshed.started_at is not None

    audits = (
        (
            await async_session.execute(
                select(AdminActionAudit).where(
                    AdminActionAudit.action
                    == admin_ops_service.CANDIDATE_SESSION_RESET_ACTION
                )
            )
        )
        .scalars()
        .all()
    )
    assert audits == []


@pytest.mark.asyncio
async def test_reset_candidate_session_noop_and_sanitized_audit_reason(async_session):
    recruiter = await create_recruiter(async_session, email="reset-noop-owner@test.com")
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    claimed_at = datetime.now(UTC) - timedelta(minutes=5)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="not_started",
        candidate_auth0_sub="auth0|candidate-reset-noop",
        claimed_at=claimed_at,
    )
    await async_session.commit()

    result = await admin_ops_service.reset_candidate_session(
        async_session,
        actor=_actor(),
        candidate_session_id=candidate_session.id,
        target_state="claimed",
        reason="  keep    claimed \n state ",
        override_if_evaluated=False,
        dry_run=False,
    )
    assert result.status == "ok"
    assert result.audit_id is not None

    audit = await _audit_by_id(async_session, result.audit_id)
    assert audit.payload_json["reason"] == "keep claimed state"
    assert audit.payload_json["noOp"] is True
    assert audit.payload_json["changedFields"] == []
    assert audit.payload_json["targetState"] == "claimed"

    refreshed = await async_session.get(type(candidate_session), candidate_session.id)
    assert refreshed is not None
    assert refreshed.status == "not_started"
    assert refreshed.claimed_at == claimed_at


@pytest.mark.asyncio
async def test_reset_candidate_session_blocks_evaluated_unless_override(async_session):
    recruiter = await create_recruiter(async_session, email="reset-eval-owner@test.com")
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="completed",
        candidate_auth0_sub="auth0|candidate-reset-eval",
        claimed_at=datetime.now(UTC) - timedelta(days=1),
        completed_at=datetime.now(UTC) - timedelta(hours=1),
    )
    async_session.add(
        EvaluationRun(
            candidate_session_id=candidate_session.id,
            scenario_version_id=candidate_session.scenario_version_id,
            status=EVALUATION_RUN_STATUS_COMPLETED,
            started_at=datetime.now(UTC) - timedelta(hours=2),
            completed_at=datetime.now(UTC) - timedelta(hours=1),
            model_name="eval-model",
            model_version="v1",
            prompt_version="p1",
            rubric_version="r1",
            day2_checkpoint_sha="day2",
            day3_final_sha="day3",
            cutoff_commit_sha="cutoff",
            transcript_reference="transcript://reset-eval",
        )
    )
    await async_session.commit()

    with pytest.raises(ApiError) as blocked:
        await admin_ops_service.reset_candidate_session(
            async_session,
            actor=_actor(),
            candidate_session_id=candidate_session.id,
            target_state="claimed",
            reason="block evaluated",
            override_if_evaluated=False,
            dry_run=False,
        )
    assert blocked.value.status_code == 409
    assert blocked.value.error_code == admin_ops_service.UNSAFE_OPERATION_ERROR_CODE

    allowed = await admin_ops_service.reset_candidate_session(
        async_session,
        actor=_actor(),
        candidate_session_id=candidate_session.id,
        target_state="claimed",
        reason="  override   evaluated \n reset ",
        override_if_evaluated=True,
        dry_run=False,
    )
    assert allowed.status == "ok"
    assert allowed.audit_id is not None
    audit = await _audit_by_id(async_session, allowed.audit_id)
    assert audit.payload_json["reason"] == "override evaluated reset"
    assert audit.payload_json["overrideIfEvaluated"] is True
    assert audit.payload_json["evaluated"] is True


@pytest.mark.asyncio
async def test_reset_candidate_session_requires_claimant_identity(async_session):
    recruiter = await create_recruiter(
        async_session, email="reset-claimant-owner@test.com"
    )
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="not_started",
        candidate_auth0_sub=None,
    )
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await admin_ops_service.reset_candidate_session(
            async_session,
            actor=_actor(),
            candidate_session_id=candidate_session.id,
            target_state="claimed",
            reason="no claimant identity",
            override_if_evaluated=False,
            dry_run=False,
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.details["requires"] == "candidate_auth0_sub"


@pytest.mark.asyncio
async def test_reset_candidate_session_not_found_and_invalid_target_state(
    async_session,
):
    with pytest.raises(HTTPException) as missing:
        await admin_ops_service.reset_candidate_session(
            async_session,
            actor=_actor(),
            candidate_session_id=999_999,
            target_state="claimed",
            reason="missing session",
            override_if_evaluated=False,
            dry_run=False,
        )
    assert missing.value.status_code == 404

    recruiter = await create_recruiter(
        async_session, email="reset-invalid-owner@test.com"
    )
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="not_started",
        candidate_auth0_sub="auth0|candidate-reset-invalid",
        claimed_at=datetime.now(UTC),
    )
    await async_session.commit()

    with pytest.raises(ValueError):
        await admin_ops_service.reset_candidate_session(
            async_session,
            actor=_actor(),
            candidate_session_id=candidate_session.id,
            target_state="invalid_state",  # type: ignore[arg-type]
            reason="invalid target",
            override_if_evaluated=False,
            dry_run=False,
        )


@pytest.mark.asyncio
async def test_requeue_job_queued_noop_and_sanitized_audit_reason(async_session):
    recruiter = await create_recruiter(
        async_session, email="requeue-noop-owner@test.com"
    )
    company = await async_session.get(Company, recruiter.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_QUEUED,
        job_type="admin-requeue-noop-unit",
    )
    await async_session.commit()

    result = await admin_ops_service.requeue_job(
        async_session,
        actor=_actor(),
        job_id=job.id,
        reason="  keep    queued \n state ",
        force=False,
    )
    assert result.previous_status == JOB_STATUS_QUEUED
    assert result.new_status == JOB_STATUS_QUEUED
    audit = await _audit_by_id(async_session, result.audit_id)
    assert audit.payload_json["reason"] == "keep queued state"
    assert audit.payload_json["noOp"] is True
    assert audit.payload_json["newStatus"] == JOB_STATUS_QUEUED


@pytest.mark.asyncio
async def test_requeue_job_dead_letter_requeues_and_clears_lock_state(async_session):
    recruiter = await create_recruiter(
        async_session, email="requeue-dead-owner@test.com"
    )
    company = await async_session.get(Company, recruiter.company_id)
    assert company is not None
    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_DEAD_LETTER,
        job_type="admin-requeue-dead-unit",
        last_error="demo failure",
        result_json={"failure": True},
        payload_json={"x": 1},
    )
    job.locked_at = datetime.now(UTC) - timedelta(minutes=30)
    job.locked_by = "worker-123"
    await async_session.commit()

    now = datetime(2026, 1, 3, 15, 0, 0)
    result = await admin_ops_service.requeue_job(
        async_session,
        actor=_actor(),
        job_id=job.id,
        reason="dead-letter retry",
        force=False,
        now=now,
    )
    assert result.previous_status == JOB_STATUS_DEAD_LETTER
    assert result.new_status == JOB_STATUS_QUEUED

    refreshed = await async_session.get(type(job), job.id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_QUEUED
    assert refreshed.locked_at is None
    assert refreshed.locked_by is None
    assert refreshed.last_error is None
    assert refreshed.result_json is None
    assert refreshed.next_run_at is not None
    assert _to_utc(refreshed.next_run_at) == _to_utc(now)


@pytest.mark.asyncio
async def test_requeue_job_stale_running_paths(async_session, monkeypatch):
    recruiter = await create_recruiter(
        async_session, email="requeue-running-stale-owner@test.com"
    )
    company = await async_session.get(Company, recruiter.company_id)
    assert company is not None
    monkeypatch.setattr(settings, "DEMO_ADMIN_JOB_STALE_SECONDS", 60)

    now = datetime.now(UTC).replace(microsecond=0)
    stale_job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_RUNNING,
        job_type="admin-requeue-running-stale-unit",
    )
    stale_job.locked_at = now - timedelta(seconds=180)
    stale_job.locked_by = "worker-stale"

    missing_lock_job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_RUNNING,
        job_type="admin-requeue-running-no-lock-unit",
    )
    missing_lock_job.locked_at = None
    missing_lock_job.locked_by = "worker-no-lock"
    await async_session.commit()

    stale_result = await admin_ops_service.requeue_job(
        async_session,
        actor=_actor(),
        job_id=stale_job.id,
        reason="stale running requeue",
        force=False,
        now=now,
    )
    stale_audit = await _audit_by_id(async_session, stale_result.audit_id)
    assert stale_audit.payload_json["staleRunning"] is True
    assert stale_audit.payload_json["staleRunningThresholdSeconds"] == 60

    no_lock_result = await admin_ops_service.requeue_job(
        async_session,
        actor=_actor(),
        job_id=missing_lock_job.id,
        reason="requeue running without lock",
        force=False,
        now=now,
    )
    no_lock_audit = await _audit_by_id(async_session, no_lock_result.audit_id)
    assert no_lock_audit.payload_json["staleRunning"] is True


@pytest.mark.asyncio
async def test_requeue_job_blocks_fresh_running_without_force(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(
        async_session, email="requeue-running-fresh-owner@test.com"
    )
    company = await async_session.get(Company, recruiter.company_id)
    assert company is not None
    monkeypatch.setattr(settings, "DEMO_ADMIN_JOB_STALE_SECONDS", 900)

    job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_RUNNING,
        job_type="admin-requeue-running-fresh-unit",
    )
    job.locked_at = datetime.now(UTC)
    job.locked_by = "worker-fresh"
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await admin_ops_service.requeue_job(
            async_session,
            actor=_actor(),
            job_id=job.id,
            reason="fresh running should block",
            force=False,
            now=datetime.now(UTC),
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == admin_ops_service.UNSAFE_OPERATION_ERROR_CODE
    assert excinfo.value.details["status"] == JOB_STATUS_RUNNING
    assert excinfo.value.details["staleRunningThresholdSeconds"] == 900

    audits = (
        (
            await async_session.execute(
                select(AdminActionAudit).where(
                    AdminActionAudit.target_id == job.id,
                    AdminActionAudit.action == admin_ops_service.JOB_REQUEUE_ACTION,
                )
            )
        )
        .scalars()
        .all()
    )
    assert audits == []


@pytest.mark.asyncio
async def test_requeue_job_force_allows_running_and_rejects_invalid_status(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(
        async_session, email="requeue-running-force-owner@test.com"
    )
    company = await async_session.get(Company, recruiter.company_id)
    assert company is not None
    monkeypatch.setattr(settings, "DEMO_ADMIN_JOB_STALE_SECONDS", 0)

    running_job = await create_job(
        async_session,
        company=company,
        status=JOB_STATUS_RUNNING,
        job_type="admin-requeue-running-force-unit",
    )
    running_job.locked_at = datetime.now(UTC)
    running_job.locked_by = "worker-force"

    blocked_job = await create_job(
        async_session,
        company=company,
        status="manual_hold",
        job_type="admin-requeue-manual-hold-unit",
    )
    await async_session.commit()

    forced = await admin_ops_service.requeue_job(
        async_session,
        actor=_actor(),
        job_id=running_job.id,
        reason="force running job requeue",
        force=True,
    )
    assert forced.new_status == JOB_STATUS_QUEUED

    forced_audit = await _audit_by_id(async_session, forced.audit_id)
    assert forced_audit.payload_json["staleRunningThresholdSeconds"] == 900

    with pytest.raises(ApiError) as excinfo:
        await admin_ops_service.requeue_job(
            async_session,
            actor=_actor(),
            job_id=blocked_job.id,
            reason="force blocked manual hold",
            force=True,
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.details["status"] == "manual_hold"


@pytest.mark.asyncio
async def test_requeue_job_not_found(async_session):
    with pytest.raises(HTTPException) as excinfo:
        await admin_ops_service.requeue_job(
            async_session,
            actor=_actor(),
            job_id="missing-job-id",
            reason="missing",
            force=False,
        )
    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_use_simulation_fallback_dry_run_is_non_mutating(async_session):
    recruiter = await create_recruiter(
        async_session, email="fallback-dry-run-owner@test.com"
    )
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    scenario_v2 = await _create_scenario_version(
        async_session,
        simulation_id=simulation.id,
        version_index=2,
    )
    simulation_id = simulation.id
    scenario_v2_id = scenario_v2.id
    prior_active = simulation.active_scenario_version_id
    await async_session.commit()

    result = await admin_ops_service.use_simulation_fallback_scenario(
        async_session,
        actor=_actor(),
        simulation_id=simulation_id,
        scenario_version_id=scenario_v2_id,
        apply_to="future_invites_only",
        reason="  dry   run fallback ",
        dry_run=True,
    )
    assert result.audit_id is None
    assert result.active_scenario_version_id == scenario_v2_id

    refreshed = await async_session.get(type(simulation), simulation_id)
    assert refreshed is not None
    assert refreshed.active_scenario_version_id == prior_active

    audits = (
        (
            await async_session.execute(
                select(AdminActionAudit).where(
                    AdminActionAudit.action
                    == admin_ops_service.SIMULATION_USE_FALLBACK_ACTION
                )
            )
        )
        .scalars()
        .all()
    )
    assert audits == []


@pytest.mark.asyncio
async def test_use_simulation_fallback_same_scenario_is_noop_with_audit(async_session):
    recruiter = await create_recruiter(
        async_session, email="fallback-noop-owner@test.com"
    )
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    await async_session.commit()

    result = await admin_ops_service.use_simulation_fallback_scenario(
        async_session,
        actor=_actor(),
        simulation_id=simulation.id,
        scenario_version_id=simulation.active_scenario_version_id or 0,
        apply_to="future_invites_only",
        reason=" no-op    fallback ",
        dry_run=False,
    )
    assert result.audit_id is not None
    assert result.active_scenario_version_id == simulation.active_scenario_version_id

    audit = await _audit_by_id(async_session, result.audit_id)
    assert audit.payload_json["reason"] == "no-op fallback"
    assert audit.payload_json["noOp"] is True


@pytest.mark.asyncio
async def test_use_simulation_fallback_pending_approval_blocked(async_session):
    recruiter = await create_recruiter(
        async_session, email="fallback-pending-owner@test.com"
    )
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    scenario_v2 = await _create_scenario_version(
        async_session,
        simulation_id=simulation.id,
        version_index=2,
    )
    simulation.pending_scenario_version_id = scenario_v2.id
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await admin_ops_service.use_simulation_fallback_scenario(
            async_session,
            actor=_actor(),
            simulation_id=simulation.id,
            scenario_version_id=scenario_v2.id,
            apply_to="future_invites_only",
            reason="pending approval blocked",
            dry_run=False,
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SCENARIO_APPROVAL_PENDING"


@pytest.mark.asyncio
async def test_use_simulation_fallback_success_keeps_existing_sessions_pinned(
    async_session,
):
    recruiter = await create_recruiter(
        async_session, email="fallback-success-owner@test.com"
    )
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    existing_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        invite_email="existing-pinned@test.com",
    )
    scenario_v1_id = existing_session.scenario_version_id
    scenario_v2 = await _create_scenario_version(
        async_session,
        simulation_id=simulation.id,
        version_index=2,
    )
    await async_session.commit()

    result = await admin_ops_service.use_simulation_fallback_scenario(
        async_session,
        actor=_actor(),
        simulation_id=simulation.id,
        scenario_version_id=scenario_v2.id,
        apply_to="future_invites_only",
        reason="  switch to   fallback v2 ",
        dry_run=False,
    )
    assert result.active_scenario_version_id == scenario_v2.id
    assert result.audit_id is not None

    refreshed_existing = await async_session.get(
        type(existing_session), existing_session.id
    )
    assert refreshed_existing is not None
    assert refreshed_existing.scenario_version_id == scenario_v1_id

    refreshed_simulation = await async_session.get(type(simulation), simulation.id)
    assert refreshed_simulation is not None
    await async_session.refresh(refreshed_simulation)
    new_session = await create_candidate_session(
        async_session,
        simulation=refreshed_simulation,
        invite_email="new-future@test.com",
    )
    await async_session.commit()
    assert new_session.scenario_version_id == scenario_v2.id

    audit = await _audit_by_id(async_session, result.audit_id)
    assert audit.payload_json["reason"] == "switch to fallback v2"
    assert audit.payload_json["noOp"] is False
    assert audit.payload_json["previousActiveScenarioVersionId"] == scenario_v1_id


@pytest.mark.asyncio
async def test_use_simulation_fallback_rejects_terminated_or_ineligible(async_session):
    recruiter = await create_recruiter(
        async_session, email="fallback-rejects-owner@test.com"
    )
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    scenario_v2 = await _create_scenario_version(
        async_session,
        simulation_id=simulation.id,
        version_index=2,
        status=SCENARIO_VERSION_STATUS_GENERATING,
    )
    await async_session.commit()

    with pytest.raises(ApiError) as ineligible:
        await admin_ops_service.use_simulation_fallback_scenario(
            async_session,
            actor=_actor(),
            simulation_id=simulation.id,
            scenario_version_id=scenario_v2.id,
            apply_to="future_invites_only",
            reason="ineligible scenario",
            dry_run=False,
        )
    assert ineligible.value.status_code == 409
    assert ineligible.value.error_code == admin_ops_service.UNSAFE_OPERATION_ERROR_CODE

    simulation.status = SIMULATION_STATUS_TERMINATED
    await async_session.commit()
    with pytest.raises(ApiError) as terminated:
        await admin_ops_service.use_simulation_fallback_scenario(
            async_session,
            actor=_actor(),
            simulation_id=simulation.id,
            scenario_version_id=scenario_v2.id,
            apply_to="future_invites_only",
            reason="terminated simulation",
            dry_run=False,
        )
    assert terminated.value.status_code == 409


@pytest.mark.asyncio
async def test_use_simulation_fallback_wrong_or_missing_targets(async_session):
    recruiter = await create_recruiter(
        async_session, email="fallback-missing-owner@test.com"
    )
    simulation_a, _ = await create_simulation(async_session, created_by=recruiter)
    simulation_b, _ = await create_simulation(async_session, created_by=recruiter)
    other_simulation_scenario = await _create_scenario_version(
        async_session,
        simulation_id=simulation_b.id,
        version_index=2,
    )
    await async_session.commit()

    with pytest.raises(HTTPException) as wrong_simulation:
        await admin_ops_service.use_simulation_fallback_scenario(
            async_session,
            actor=_actor(),
            simulation_id=simulation_a.id,
            scenario_version_id=other_simulation_scenario.id,
            apply_to="future_invites_only",
            reason="wrong simulation scenario",
            dry_run=False,
        )
    assert wrong_simulation.value.status_code == 404

    with pytest.raises(HTTPException) as missing_simulation:
        await admin_ops_service.use_simulation_fallback_scenario(
            async_session,
            actor=_actor(),
            simulation_id=999_999,
            scenario_version_id=other_simulation_scenario.id,
            apply_to="future_invites_only",
            reason="missing simulation",
            dry_run=False,
        )
    assert missing_simulation.value.status_code == 404

    with pytest.raises(HTTPException) as missing_scenario:
        await admin_ops_service.use_simulation_fallback_scenario(
            async_session,
            actor=_actor(),
            simulation_id=simulation_a.id,
            scenario_version_id=999_999,
            apply_to="future_invites_only",
            reason="missing scenario",
            dry_run=False,
        )
    assert missing_scenario.value.status_code == 404
