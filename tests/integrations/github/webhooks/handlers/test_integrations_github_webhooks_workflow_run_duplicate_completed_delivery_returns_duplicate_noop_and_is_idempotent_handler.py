from __future__ import annotations

import pytest

from tests.integrations.github.webhooks.handlers.integrations_github_webhooks_workflow_run_handler_utils import *


@pytest.mark.asyncio
async def test_duplicate_completed_delivery_returns_duplicate_noop_and_is_idempotent(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="webhook-noop@winoe.dev"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        with_default_schedule=True,
    )

    run_id = 66550
    head_sha = "noop-head-sha"
    completed_at = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks[1],
        code_repo_path="acme/noop-repo",
        workflow_run_id=str(run_id),
        workflow_run_attempt=3,
        workflow_run_status="completed",
        workflow_run_conclusion="success",
        workflow_run_completed_at=completed_at,
        commit_sha=head_sha,
        last_run_at=completed_at,
    )
    await async_session.commit()

    payload = _workflow_payload(
        run_id=run_id,
        repo_full_name="acme/noop-repo",
        head_sha=head_sha,
        run_attempt=3,
        completed_at="2026-03-13T12:00:00Z",
    )

    first = await workflow_run.process_workflow_run_completed_event(
        async_session,
        payload=payload,
        delivery_id="delivery-noop-1",
    )
    second = await workflow_run.process_workflow_run_completed_event(
        async_session,
        payload=payload,
        delivery_id="delivery-noop-2",
    )

    assert first.outcome == "duplicate_noop"
    assert first.enqueued_artifact_parse is True
    assert second.outcome == "duplicate_noop"
    assert second.enqueued_artifact_parse is False
    assert first.submission_id == submission.id
    assert second.submission_id == submission.id

    jobs = (
        await async_session.execute(
            select(Job).where(
                Job.job_type == workflow_run.GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE
            )
        )
    ).scalars()
    assert len(list(jobs)) == 1
