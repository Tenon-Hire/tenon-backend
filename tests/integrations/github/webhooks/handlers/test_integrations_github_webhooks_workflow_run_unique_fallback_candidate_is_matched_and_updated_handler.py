from __future__ import annotations

import pytest

from tests.integrations.github.webhooks.handlers.integrations_github_webhooks_workflow_run_handler_utils import *


@pytest.mark.asyncio
async def test_unique_fallback_candidate_is_matched_and_updated(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="webhook-fallback@winoe.dev"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="webhook-fallback-candidate@winoe.dev",
        with_default_schedule=True,
    )

    original_last_run_at = datetime(2026, 3, 13, 8, 10, tzinfo=UTC)
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks[1],
        code_repo_path="acme/fallback-match",
        commit_sha="fallback-sha",
        workflow_run_status="queued",
        last_run_at=original_last_run_at,
    )
    await async_session.commit()

    result = await workflow_run.process_workflow_run_completed_event(
        async_session,
        payload=_workflow_payload(
            run_id=60601,
            repo_full_name="acme/fallback-match",
            head_sha="fallback-sha",
            completed_at=None,
        ),
        delivery_id="delivery-fallback-matched",
    )

    assert result.outcome == "updated_status"
    assert result.reason_code == "matched_by_repo_head_sha"
    assert result.submission_id == submission.id

    await async_session.refresh(submission)
    assert submission.workflow_run_id == "60601"
    assert submission.workflow_run_status == "completed"
    assert submission.last_run_at is not None
    observed_last_run_at = submission.last_run_at
    if observed_last_run_at.tzinfo is None:
        observed_last_run_at = observed_last_run_at.replace(tzinfo=UTC)
    assert observed_last_run_at == original_last_run_at
