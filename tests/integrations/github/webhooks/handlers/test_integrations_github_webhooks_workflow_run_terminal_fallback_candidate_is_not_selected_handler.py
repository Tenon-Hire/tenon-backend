from __future__ import annotations

import pytest

from tests.integrations.github.webhooks.handlers.integrations_github_webhooks_workflow_run_handler_utils import *


@pytest.mark.asyncio
async def test_terminal_fallback_candidate_is_not_selected(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="webhook-terminal@winoe.dev"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        with_default_schedule=True,
    )

    await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks[1],
        code_repo_path="acme/terminal-repo",
        commit_sha="terminal-sha",
        workflow_run_status="completed",
        workflow_run_conclusion="success",
        workflow_run_completed_at=datetime(2026, 3, 13, 7, 30, tzinfo=UTC),
        last_run_at=datetime(2026, 3, 13, 7, 30, tzinfo=UTC),
    )
    await async_session.commit()

    result = await workflow_run.process_workflow_run_completed_event(
        async_session,
        payload=_workflow_payload(
            run_id=808001,
            repo_full_name="acme/terminal-repo",
            head_sha="terminal-sha",
        ),
        delivery_id="delivery-terminal-excluded",
    )

    assert result.outcome == "unmatched"
    assert result.reason_code == "mapping_unmatched"
    assert result.enqueued_artifact_parse is False
