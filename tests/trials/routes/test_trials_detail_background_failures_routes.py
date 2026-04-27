from __future__ import annotations

from app.shared.database.shared_database_models_model import Company
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
)
from tests.shared.factories import (
    create_candidate_session,
    create_job,
    create_talent_partner,
    create_trial,
)


async def test_trial_detail_includes_related_background_failure(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="trial-failures-owner@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="trial-failures-candidate@test.com",
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    failed = await create_job(
        async_session,
        company=company,
        job_type="transcribe_recording",
        status=JOB_STATUS_DEAD_LETTER,
        candidate_session=candidate_session,
        last_error="unsupported file format token=super-secret",
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/trials/{trial.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    failures = body["backgroundFailures"]
    assert failures["hasFailedJobs"] is True
    assert failures["failedJobsCount"] == 1
    assert failures["latestFailure"]["jobId"] == failed.id
    assert failures["latestFailure"]["jobType"] == "transcribe_recording"
    assert failures["latestFailure"]["failedAt"] is not None
    assert failures["latestFailure"]["reason"] == (
        "Media transcription failed: unsupported file format token=[redacted]"
    )
    assert "super-secret" not in response.text


async def test_trial_detail_reports_no_background_failures_when_none_exist(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="trial-no-failures-owner@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    await async_session.commit()

    response = await async_client.get(
        f"/api/trials/{trial.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )

    assert response.status_code == 200, response.text
    assert response.json()["backgroundFailures"] == {
        "hasFailedJobs": False,
        "failedJobsCount": 0,
        "latestFailure": None,
    }


async def test_trial_detail_includes_payload_and_correlation_background_failures(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="trial-failures-metadata-owner@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    await create_job(
        async_session,
        company=company,
        job_type="evaluation_run",
        status=JOB_STATUS_DEAD_LETTER,
        payload_json={"trialId": trial.id},
        last_error="evaluation failed",
    )
    await create_job(
        async_session,
        company=company,
        job_type="project_brief_sync",
        status=JOB_STATUS_DEAD_LETTER,
        correlation_id=f"trial:{trial.id}:winoe-report",
        last_error="provider timed out",
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/trials/{trial.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )

    assert response.status_code == 200, response.text
    failures = response.json()["backgroundFailures"]
    assert failures["hasFailedJobs"] is True
    assert failures["failedJobsCount"] == 2
    assert failures["latestFailure"]["jobId"]


async def test_trial_detail_avoids_correlation_and_payload_false_positives(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="trial-failures-false-positive-owner@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    await create_job(
        async_session,
        company=company,
        job_type="evaluation_run",
        status=JOB_STATUS_DEAD_LETTER,
        correlation_id=f"trial:{trial.id}999",
        last_error="evaluation failed",
    )
    await create_job(
        async_session,
        company=company,
        job_type="evaluation_run",
        status=JOB_STATUS_DEAD_LETTER,
        payload_json={"trialId": trial.id + 999},
        last_error="evaluation failed",
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/trials/{trial.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )

    assert response.status_code == 200, response.text
    assert response.json()["backgroundFailures"]["hasFailedJobs"] is False


async def test_trial_detail_does_not_include_other_trial_failures(
    async_client, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="trial-scoped-failures-owner@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    other_trial, _other_tasks = await create_trial(
        async_session,
        created_by=talent_partner,
        title="Other Trial",
    )
    other_candidate_session = await create_candidate_session(
        async_session,
        trial=other_trial,
        invite_email="other-trial-candidate@test.com",
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    await create_job(
        async_session,
        company=company,
        job_type="evaluation_run",
        status=JOB_STATUS_DEAD_LETTER,
        candidate_session=other_candidate_session,
        last_error="evaluation failed",
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/trials/{trial.id}",
        headers={"x-dev-user-email": talent_partner.email},
    )

    assert response.status_code == 200, response.text
    assert response.json()["backgroundFailures"]["hasFailedJobs"] is False


async def test_trial_detail_access_control_still_hides_other_company_trial_failure(
    async_client, async_session
):
    owner = await create_talent_partner(
        async_session, email="trial-failures-company-a@test.com"
    )
    outsider = await create_talent_partner(
        async_session, email="trial-failures-company-b@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=owner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="trial-company-a-candidate@test.com",
    )
    company = await async_session.get(Company, owner.company_id)
    assert company is not None
    await create_job(
        async_session,
        company=company,
        job_type="evaluation_run",
        status=JOB_STATUS_DEAD_LETTER,
        candidate_session=candidate_session,
        last_error="model_timeout",
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/trials/{trial.id}",
        headers={"x-dev-user-email": outsider.email},
    )

    assert response.status_code == 404


async def test_trial_detail_excludes_cross_company_failure_even_with_matching_metadata(
    async_client, async_session
):
    owner = await create_talent_partner(
        async_session, email="trial-failures-owner-company@test.com"
    )
    other_partner = await create_talent_partner(
        async_session, email="trial-failures-other-company@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=owner)
    other_company = await async_session.get(Company, other_partner.company_id)
    assert other_company is not None
    await create_job(
        async_session,
        company=other_company,
        job_type="evaluation_run",
        status=JOB_STATUS_DEAD_LETTER,
        correlation_id=f"trial:{trial.id}",
        payload_json={"trialId": trial.id},
        last_error="evaluation failed",
    )
    await async_session.commit()

    response = await async_client.get(
        f"/api/trials/{trial.id}",
        headers={"x-dev-user-email": owner.email},
    )

    assert response.status_code == 200, response.text
    assert response.json()["backgroundFailures"]["hasFailedJobs"] is False
