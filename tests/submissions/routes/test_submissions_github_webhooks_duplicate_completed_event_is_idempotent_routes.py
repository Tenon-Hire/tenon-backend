from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_github_webhooks_api_utils import *


@pytest.mark.asyncio
async def test_github_webhook_duplicate_completed_event_is_idempotent(
    async_client,
    async_session,
    monkeypatch,
):
    webhook_routes.rate_limit.limiter.reset()
    secret = "test-webhook-secret"
    monkeypatch.setattr(webhook_routes.settings.github, "GITHUB_WEBHOOK_SECRET", secret)

    talent_partner = await create_talent_partner(
        async_session, email="webhooks-2@winoe.dev"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        with_default_schedule=True,
    )

    workflow_run_id = 777123
    repo_full_name = "acme/webhook-repo-dup"
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
        head_sha="sha-dup",
        run_attempt=3,
    )
    raw_body = json.dumps(payload).encode("utf-8")

    first = await async_client.post(
        "/api/github/webhooks",
        content=raw_body,
        headers=_signed_headers(
            secret=secret,
            raw_body=raw_body,
            delivery_id="delivery-dup-1",
        ),
    )
    second = await async_client.post(
        "/api/github/webhooks",
        content=raw_body,
        headers=_signed_headers(
            secret=secret,
            raw_body=raw_body,
            delivery_id="delivery-dup-2",
        ),
    )

    assert first.status_code == 202, first.text
    assert second.status_code == 202, second.text

    await async_session.refresh(submission)
    assert submission.workflow_run_status == "completed"
    assert submission.workflow_run_attempt == 3

    idempotency_key = build_artifact_parse_job_idempotency_key(
        submission_id=submission.id,
        workflow_run_id=workflow_run_id,
        workflow_run_attempt=3,
    )
    jobs = (
        await async_session.execute(
            select(Job).where(
                Job.job_type == GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE,
                Job.idempotency_key == idempotency_key,
            )
        )
    ).scalars()
    assert len(list(jobs)) == 1
