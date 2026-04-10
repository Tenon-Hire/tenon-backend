from __future__ import annotations

import pytest

from tests.integrations.github.webhooks.handlers.integrations_github_webhooks_workflow_run_handler_utils import *


@pytest.mark.asyncio
async def test_direct_match_sets_last_run_at_when_completed_at_missing(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="webhook-last-run@winoe.dev"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="webhook-last-run-candidate@winoe.dev",
        with_default_schedule=True,
    )
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks[1],
        code_repo_path="acme/last-run-fallback",
        workflow_run_id="515151",
        workflow_run_status="queued",
        last_run_at=None,
    )
    await async_session.commit()

    result = await workflow_run.process_workflow_run_completed_event(
        async_session,
        payload=_workflow_payload(
            run_id=515151,
            repo_full_name="acme/last-run-fallback",
            head_sha=None,
            completed_at=None,
        ),
        delivery_id="delivery-last-run-autoset",
    )

    assert result.outcome == "updated_status"
    await async_session.refresh(submission)
    assert submission.workflow_run_status == "completed"
    assert submission.workflow_run_completed_at is None
    assert submission.last_run_at is not None
