from __future__ import annotations

import pytest

from tests.submissions.routes.submissions_github_webhooks_api_utils import *


@pytest.mark.asyncio
async def test_github_webhook_unmatched_payload_is_accepted_without_mutation(
    async_client,
    async_session,
    monkeypatch,
):
    webhook_routes.rate_limit.limiter.reset()
    secret = "test-webhook-secret"
    monkeypatch.setattr(webhook_routes.settings.github, "GITHUB_WEBHOOK_SECRET", secret)

    talent_partner = await create_talent_partner(
        async_session, email="webhooks-3@winoe.dev"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        with_default_schedule=True,
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks[1],
        content_text="day2",
        code_repo_path="acme/matched-repo",
        workflow_run_id="123",
        workflow_run_status="queued",
        workflow_run_conclusion=None,
    )
    await async_session.commit()

    payload = _build_workflow_run_payload(
        run_id=999777,
        repo_full_name="acme/unmatched-repo",
        head_sha="sha-no-match",
    )
    raw_body = json.dumps(payload).encode("utf-8")

    response = await async_client.post(
        "/api/github/webhooks",
        content=raw_body,
        headers=_signed_headers(
            secret=secret,
            raw_body=raw_body,
            delivery_id="delivery-unmatched",
        ),
    )

    assert response.status_code == 202, response.text
    assert response.json() == {"status": "accepted"}

    await async_session.refresh(submission)
    assert submission.workflow_run_id == "123"
    assert submission.workflow_run_status == "queued"
    assert submission.workflow_run_conclusion is None
    assert submission.workflow_run_attempt is None
    assert submission.commit_sha is None

    jobs = (
        await async_session.execute(
            select(Job).where(Job.job_type == GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE)
        )
    ).scalars()
    assert list(jobs) == []
