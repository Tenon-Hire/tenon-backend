from __future__ import annotations

from app.shared.database.shared_database_models_model import Company, Job, User
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_DEAD_LETTER,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
)
from app.shared.jobs.shared_jobs_failure_reasons_service import human_failure_reason
from tests.shared.factories import (
    create_candidate_session,
    create_job,
    create_talent_partner,
    create_trial,
)


def _admin_headers(email: str = "operator@test.com") -> dict[str, str]:
    return {"x-dev-user-email": email}


def _talent_partner_headers(email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer talent_partner:{email}"}


def _candidate_headers(email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer candidate:{email}"}


async def _create_admin_user(async_session, email: str = "operator@test.com") -> User:
    admin = User(
        name=email.split("@")[0],
        email=email,
        role="admin",
        company_id=None,
        password_hash="",
    )
    async_session.add(admin)
    await async_session.flush()
    return admin


async def _failed_job_fixture(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="owner-admin-jobs@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="candidate-admin-jobs@test.com",
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    failed = await create_job(
        async_session,
        company=company,
        job_type="evaluation_run",
        status=JOB_STATUS_DEAD_LETTER,
        attempt=7,
        max_attempts=7,
        candidate_session=candidate_session,
        last_error=(
            "Traceback (most recent call last): Authorization: Bearer secret-token "
            "Evaluation provider timed out"
        ),
        payload_json={"candidateSessionId": candidate_session.id},
    )
    await create_job(
        async_session,
        company=company,
        job_type="queued_job",
        status=JOB_STATUS_QUEUED,
    )
    await async_session.commit()
    return failed, trial, candidate_session


async def test_admin_can_list_failed_jobs_with_safe_metadata(
    async_client, async_session
):
    failed, trial, candidate_session = await _failed_job_fixture(async_session)
    admin = await _create_admin_user(async_session)
    await async_session.commit()

    response = await async_client.get(
        "/api/admin/jobs/failed?limit=10&offset=0",
        headers=_admin_headers(admin.email),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 10
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["jobId"] == failed.id
    assert item["jobType"] == "evaluation_run"
    assert item["status"] == JOB_STATUS_DEAD_LETTER
    assert item["trialId"] == trial.id
    assert item["candidateSessionId"] == candidate_session.id
    assert item["attempts"] == 7
    assert item["maxAttempts"] == 7
    assert item["failedAt"] is not None
    assert item["failureCode"] == "evaluation"
    assert item["failureReason"] == (
        "Evaluation provider timed out while generating the Winoe Report."
    )
    assert "secret-token" not in response.text
    assert "Traceback" not in response.text


async def test_admin_can_list_failed_jobs_with_local_dev_header(
    async_client, async_session
):
    failed, _trial, _candidate_session = await _failed_job_fixture(async_session)
    admin = User(
        name="QA Admin",
        email="qa-admin-operator@test.com",
        role="admin",
        company_id=None,
        password_hash="",
    )
    async_session.add(admin)
    await async_session.commit()

    response = await async_client.get(
        "/api/admin/jobs/failed",
        headers={"x-dev-user-email": admin.email},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["jobId"] == failed.id


async def test_failed_jobs_list_rejects_non_admin_callers(async_client, async_session):
    talent_partner = await create_talent_partner(
        async_session, email="non-admin@test.com"
    )
    await async_session.commit()

    talent_response = await async_client.get(
        "/api/admin/jobs/failed",
        headers=_talent_partner_headers(talent_partner.email),
    )
    candidate_response = await async_client.get(
        "/api/admin/jobs/failed",
        headers=_candidate_headers("candidate-denied@test.com"),
    )
    unauthenticated_response = await async_client.get("/api/admin/jobs/failed")

    assert talent_response.status_code == 403
    assert candidate_response.status_code == 403
    assert unauthenticated_response.status_code == 401


async def test_failed_jobs_list_paginates(async_client, async_session):
    talent_partner = await create_talent_partner(
        async_session, email="owner-admin-jobs-page@test.com"
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    first = await create_job(
        async_session,
        company=company,
        job_type="first_failed",
        status=JOB_STATUS_DEAD_LETTER,
    )
    second = await create_job(
        async_session,
        company=company,
        job_type="second_failed",
        status=JOB_STATUS_DEAD_LETTER,
    )
    await async_session.commit()
    admin = await _create_admin_user(
        async_session, email="operator-pagination@test.com"
    )
    await async_session.commit()

    response = await async_client.get(
        "/api/admin/jobs/failed?limit=1&offset=1",
        headers=_admin_headers(admin.email),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["jobId"] in {first.id, second.id}


async def test_admin_can_retry_dead_letter_job(async_client, async_session):
    failed, _trial, _candidate_session = await _failed_job_fixture(async_session)
    failed_id = failed.id
    admin = await _create_admin_user(async_session, email="operator-retry@test.com")
    await async_session.commit()

    response = await async_client.post(
        f"/api/admin/jobs/{failed_id}/retry",
        headers=_admin_headers(admin.email),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["jobId"] == failed_id
    assert body["status"] == JOB_STATUS_QUEUED
    async_session.expire_all()
    refreshed = await async_session.get(Job, failed_id)
    assert refreshed is not None
    assert refreshed.status == JOB_STATUS_QUEUED
    assert refreshed.last_error is None
    assert refreshed.locked_at is None
    assert refreshed.locked_by is None
    assert refreshed.result_json is None
    assert refreshed.next_run_at is not None


async def test_retry_unknown_and_non_retryable_jobs(async_client, async_session):
    talent_partner = await create_talent_partner(
        async_session, email="owner-admin-jobs-retry@test.com"
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    running = await create_job(
        async_session,
        company=company,
        job_type="running_job",
        status=JOB_STATUS_RUNNING,
    )
    await async_session.commit()
    admin = await _create_admin_user(
        async_session, email="operator-retry-conflict@test.com"
    )
    await async_session.commit()

    missing_response = await async_client.post(
        "/api/admin/jobs/missing-job-id/retry",
        headers=_admin_headers(admin.email),
    )
    running_response = await async_client.post(
        f"/api/admin/jobs/{running.id}/retry",
        headers=_admin_headers(admin.email),
    )

    assert missing_response.status_code == 404
    assert missing_response.json()["errorCode"] == "JOB_NOT_FOUND"
    assert running_response.status_code == 409
    assert running_response.json()["errorCode"] == "JOB_NOT_RETRYABLE"


async def test_retry_rejects_non_admin_callers(async_client, async_session):
    failed, _trial, _candidate_session = await _failed_job_fixture(async_session)
    talent_partner = await create_talent_partner(
        async_session, email="retry-non-admin@test.com"
    )
    await async_session.commit()

    talent_response = await async_client.post(
        f"/api/admin/jobs/{failed.id}/retry",
        headers=_talent_partner_headers(talent_partner.email),
    )
    candidate_response = await async_client.post(
        f"/api/admin/jobs/{failed.id}/retry",
        headers=_candidate_headers("candidate-retry-denied@test.com"),
    )
    unauthenticated_response = await async_client.post(
        f"/api/admin/jobs/{failed.id}/retry"
    )

    assert talent_response.status_code == 403
    assert candidate_response.status_code == 403
    assert unauthenticated_response.status_code == 401


def test_human_failure_reason_redacts_common_secret_and_stack_trace_shapes():
    assert (
        human_failure_reason(
            job_type="evaluation_run",
            error=(
                "Traceback (most recent call last): File "
                '"worker.py", line 1 Evaluation failed Authorization: Bearer bearer-secret'
            ),
        )
        == "Evaluation failed while generating the Winoe Report."
    )
    assert "api-secret" not in human_failure_reason(
        job_type="sync_job",
        error="provider failed api_key=api-secret",
    )
    assert "github-secret" not in human_failure_reason(
        job_type="github_sync",
        error="GitHub request failed github_token=github-secret",
    )
    assert "plain-token" not in human_failure_reason(
        job_type="sync_job",
        error="provider failed token=plain-token",
    )


def test_human_failure_reason_uses_winoe_terms_for_evaluation_failures():
    reason = human_failure_reason(
        job_type="evaluation_run",
        error="evaluation failed while building report",
    )

    assert reason == "Evaluation failed while generating the Winoe Report."
    assert " ".join(("Fit", "Profile")) not in reason
    assert " ".join(("Fit", "Score")) not in reason


def test_human_failure_reason_handles_provider_timeout_unknown_and_transcription():
    assert (
        human_failure_reason(
            job_type="provider_call",
            error="request timed out after 30 seconds",
        )
        == "Provider timed out while processing the job."
    )
    assert human_failure_reason(
        job_type="sync_job",
        error="unexpected value",
    ) == (
        "Sync Job failed with an unclassified error. "
        "Use the job id to inspect server logs."
    )
    assert (
        human_failure_reason(
            job_type="transcribe_recording",
            error="unsupported file format",
        )
        == "Media transcription failed: unsupported file format"
    )
