from __future__ import annotations

import pytest

from tests.integrations.github.webhooks.handlers.integrations_github_webhooks_workflow_run_handler_utils import *


@pytest.mark.asyncio
async def test_ambiguous_direct_workflow_run_id_match_returns_unmatched(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="webhook-direct@winoe.dev"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    first_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="webhook-direct-first@winoe.dev",
        with_default_schedule=True,
    )
    second_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="webhook-direct-second@winoe.dev",
        with_default_schedule=True,
    )

    for candidate_session in (first_session, second_session):
        await create_submission(
            async_session,
            candidate_session=candidate_session,
            task=tasks[1],
            code_repo_path="acme/direct-ambiguous",
            workflow_run_id="9991",
            last_run_at=datetime(2026, 3, 13, 9, 0, tzinfo=UTC),
        )
    await async_session.commit()

    result = await workflow_run.process_workflow_run_completed_event(
        async_session,
        payload=_workflow_payload(
            run_id=9991,
            repo_full_name="acme/direct-ambiguous",
            head_sha="unused",
        ),
        delivery_id="delivery-direct-ambiguous",
    )

    assert result.outcome == "unmatched"
    assert result.reason_code == "mapping_ambiguous_workflow_run_id"
    assert result.submission_id is None
