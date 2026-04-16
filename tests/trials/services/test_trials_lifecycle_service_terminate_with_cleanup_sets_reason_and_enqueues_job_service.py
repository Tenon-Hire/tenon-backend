from __future__ import annotations

import pytest

from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
)
from tests.shared.factories import create_candidate_session, create_job
from tests.trials.services.trials_lifecycle_service_utils import *


@pytest.mark.asyncio
async def test_terminate_with_cleanup_sets_reason_and_enqueues_job(async_session):
    company = Company(name="Terminate Cleanup Co")
    async_session.add(company)
    await async_session.flush()

    owner = User(
        name="Owner",
        email="owner-terminate-cleanup@test.com",
        role="talent_partner",
        company_id=company.id,
        password_hash="",
    )
    async_session.add(owner)
    await async_session.flush()

    trial = Trial(
        company_id=company.id,
        title="Terminate with cleanup",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Termination metadata",
        scenario_template="default-5day-node-postgres",
        created_by=owner.id,
        status=sim_service.TRIAL_STATUS_GENERATING,
        generating_at=datetime.now(UTC),
    )
    async_session.add(trial)
    await async_session.flush()
    await _attach_active_scenario(async_session, trial)
    trial.status = sim_service.TRIAL_STATUS_READY_FOR_REVIEW
    trial.ready_for_review_at = datetime.now(UTC)
    await async_session.commit()

    result = await sim_service.terminate_trial_with_cleanup(
        async_session,
        trial_id=trial.id,
        actor_user_id=owner.id,
        reason="regenerate",
    )
    assert result.trial.status == sim_service.TRIAL_STATUS_TERMINATED
    assert result.trial.terminated_reason == "regenerate"
    assert result.trial.terminated_by_talent_partner_id == owner.id
    assert len(result.cleanup_job_ids) == 1

    job_rows = (
        await async_session.execute(
            select(Job).where(
                Job.job_type == "trial_cleanup",
                Job.idempotency_key == f"trial_cleanup:{trial.id}",
            )
        )
    ).scalars()
    jobs = list(job_rows)
    assert len(jobs) == 1
    assert jobs[0].id == result.cleanup_job_ids[0]
    assert jobs[0].payload_json["trialId"] == trial.id
    assert jobs[0].payload_json["reason"] == "regenerate"


@pytest.mark.asyncio
async def test_terminate_with_cleanup_expires_pending_invites_and_cancels_trial_jobs(
    async_session,
):
    company = Company(name="Terminate Cleanup Company")
    async_session.add(company)
    await async_session.flush()

    owner = User(
        name="Owner",
        email="owner-terminate-side-effects@test.com",
        role="talent_partner",
        company_id=company.id,
        password_hash="",
    )
    async_session.add(owner)
    await async_session.flush()

    trial = Trial(
        company_id=company.id,
        title="Terminate Side Effects",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Termination side effects",
        scenario_template="default-5day-node-postgres",
        created_by=owner.id,
        status=sim_service.TRIAL_STATUS_GENERATING,
        generating_at=datetime.now(UTC),
    )
    other_trial = Trial(
        company_id=company.id,
        title="Other Trial",
        role="Backend Engineer",
        tech_stack="Python",
        seniority="Mid",
        focus="Unrelated trial",
        scenario_template="default-5day-node-postgres",
        created_by=owner.id,
        status=sim_service.TRIAL_STATUS_GENERATING,
        generating_at=datetime.now(UTC),
    )
    async_session.add_all([trial, other_trial])
    await async_session.flush()
    await _attach_active_scenario(async_session, trial)
    await _attach_active_scenario(async_session, other_trial)
    trial.status = sim_service.TRIAL_STATUS_READY_FOR_REVIEW
    trial.ready_for_review_at = datetime.now(UTC)
    other_trial.status = sim_service.TRIAL_STATUS_READY_FOR_REVIEW
    other_trial.ready_for_review_at = datetime.now(UTC)

    pending_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="pending-terminate@test.com",
        candidate_name="Pending Terminate",
        status="not_started",
        expires_in_days=14,
    )
    other_session = await create_candidate_session(
        async_session,
        trial=other_trial,
        invite_email="other-terminate@test.com",
        candidate_name="Other Terminate",
        status="not_started",
        expires_in_days=14,
    )
    pending_session.github_username = "pending-user"
    other_session.github_username = "other-user"
    await async_session.flush()

    queued_job = await create_job(
        async_session,
        company=company,
        job_type="candidate_completed_notification",
        status=JOB_STATUS_QUEUED,
        idempotency_key=f"candidate_completed:{pending_session.id}",
        payload_json={
            "trialId": trial.id,
            "candidateSessionId": pending_session.id,
        },
        candidate_session=pending_session,
        correlation_id=f"candidate_session:{pending_session.id}:candidate_completed_notification",
    )
    running_job = await create_job(
        async_session,
        company=company,
        job_type="winoe_report_ready_notification",
        status=JOB_STATUS_RUNNING,
        idempotency_key=f"winoe_report_ready:{pending_session.id}",
        payload_json={
            "trialId": trial.id,
            "candidateSessionId": pending_session.id,
        },
        candidate_session=pending_session,
        correlation_id=f"candidate_session:{pending_session.id}:winoe_report_ready_notification",
    )
    other_job = await create_job(
        async_session,
        company=company,
        job_type="candidate_completed_notification",
        status=JOB_STATUS_QUEUED,
        idempotency_key=f"candidate_completed:{other_session.id}",
        payload_json={
            "trialId": other_trial.id,
            "candidateSessionId": other_session.id,
        },
        candidate_session=other_session,
        correlation_id=f"candidate_session:{other_session.id}:candidate_completed_notification",
    )
    await async_session.commit()

    result = await sim_service.terminate_trial_with_cleanup(
        async_session,
        trial_id=trial.id,
        actor_user_id=owner.id,
        reason="cleanup",
    )

    assert result.trial.status == sim_service.TRIAL_STATUS_TERMINATED
    assert result.trial.terminated_reason == "cleanup"
    assert result.trial.terminated_by_talent_partner_id == owner.id
    assert len(result.cleanup_job_ids) == 1

    refreshed_session = await async_session.get(
        type(pending_session), pending_session.id
    )
    assert refreshed_session is not None
    assert refreshed_session.status == "expired"
    assert refreshed_session.expires_at is not None

    refreshed_queued_job = await async_session.get(type(queued_job), queued_job.id)
    refreshed_running_job = await async_session.get(type(running_job), running_job.id)
    refreshed_other_job = await async_session.get(type(other_job), other_job.id)
    assert refreshed_queued_job is not None
    assert refreshed_running_job is not None
    assert refreshed_other_job is not None
    assert refreshed_queued_job.status == JOB_STATUS_DEAD_LETTER
    assert refreshed_running_job.status == JOB_STATUS_DEAD_LETTER
    assert refreshed_other_job.status == JOB_STATUS_QUEUED
    assert refreshed_queued_job.last_error == "trial_terminated"
    assert refreshed_running_job.last_error == "trial_terminated"
