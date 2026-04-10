from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_github_webhooks_api_utils import *


@pytest.mark.asyncio
async def test_github_webhook_workflow_run_completed_updates_and_enqueues_job_once(
    async_client,
    async_session,
    monkeypatch,
):
    webhook_routes.rate_limit.limiter.reset()
    secret = "test-webhook-secret"
    monkeypatch.setattr(webhook_routes.settings.github, "GITHUB_WEBHOOK_SECRET", secret)

    talent_partner = await create_talent_partner(
        async_session, email="webhooks-1@winoe.dev"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        with_default_schedule=True,
    )

    workflow_run_id = 555001
    repo_full_name = "acme/webhook-repo"
    head_sha = "abcdef123"
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks[1],
        content_text="day2",
        code_repo_path=repo_full_name,
        workflow_run_id=str(workflow_run_id),
    )
    await async_session.commit()

    payload = _build_workflow_run_payload(
        run_id=workflow_run_id,
        repo_full_name=repo_full_name,
        head_sha=head_sha,
        run_attempt=2,
    )
    raw_body = json.dumps(payload).encode("utf-8")
    response = await async_client.post(
        "/api/github/webhooks",
        content=raw_body,
        headers=_signed_headers(
            secret=secret,
            raw_body=raw_body,
            delivery_id="delivery-updated-status",
        ),
    )

    assert response.status_code == 202, response.text
    assert response.json() == {"status": "accepted"}

    await async_session.refresh(submission)
    assert submission.workflow_run_id == str(workflow_run_id)
    assert submission.workflow_run_attempt == 2
    assert submission.workflow_run_status == "completed"
    assert submission.workflow_run_conclusion == "success"
    assert submission.commit_sha == head_sha

    assert submission.workflow_run_completed_at is not None
    observed_completed_at = submission.workflow_run_completed_at
    if observed_completed_at.tzinfo is None:
        observed_completed_at = observed_completed_at.replace(tzinfo=UTC)
    assert observed_completed_at == datetime(2026, 3, 13, 12, 0, tzinfo=UTC)

    assert submission.last_run_at is not None
    observed_last_run_at = submission.last_run_at
    if observed_last_run_at.tzinfo is None:
        observed_last_run_at = observed_last_run_at.replace(tzinfo=UTC)
    assert observed_last_run_at == datetime(2026, 3, 13, 12, 0, tzinfo=UTC)

    idempotency_key = build_artifact_parse_job_idempotency_key(
        submission_id=submission.id,
        workflow_run_id=workflow_run_id,
        workflow_run_attempt=2,
    )
    jobs = (
        await async_session.execute(
            select(Job).where(
                Job.job_type == GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE,
                Job.idempotency_key == idempotency_key,
            )
        )
    ).scalars()
    jobs_list = list(jobs)
    assert len(jobs_list) == 1
    assert jobs_list[0].candidate_session_id == candidate_session.id
