from __future__ import annotations

import pytest

from tests.integrations.github.webhooks.handlers.integrations_github_webhooks_workflow_run_handler_utils import *


@pytest.mark.asyncio
async def test_process_workflow_run_completed_event_company_unresolved_returns_unmatched(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session,
        email="webhook-no-company@winoe.dev",
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
        code_repo_path="acme/no-company",
        workflow_run_id="12345",
        last_run_at=datetime(2026, 3, 13, 10, 0, tzinfo=UTC),
    )
    await async_session.commit()

    async def _return_none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(workflow_run, "_company_id_for_submission", _return_none)

    result = await workflow_run.process_workflow_run_completed_event(
        async_session,
        payload=_workflow_payload(
            run_id=12345,
            repo_full_name="acme/no-company",
        ),
        delivery_id="delivery-no-company",
    )

    assert result.outcome == "unmatched"
    assert result.reason_code == "submission_company_unresolved"
    assert result.submission_id == submission.id
    assert result.workflow_run_id == 12345
