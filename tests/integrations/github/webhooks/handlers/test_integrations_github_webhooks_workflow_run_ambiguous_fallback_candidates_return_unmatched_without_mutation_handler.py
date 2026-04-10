from __future__ import annotations

import pytest

from tests.integrations.github.webhooks.handlers.integrations_github_webhooks_workflow_run_handler_utils import *


@pytest.mark.asyncio
async def test_ambiguous_fallback_candidates_return_unmatched_without_mutation(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="webhook-ambig@winoe.dev"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    first_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="webhook-ambig-first@winoe.dev",
        with_default_schedule=True,
    )
    second_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="webhook-ambig-second@winoe.dev",
        with_default_schedule=True,
    )

    repo_full_name = "acme/ambiguous-repo"
    head_sha = "ambiguous-sha"

    first = await create_submission(
        async_session,
        candidate_session=first_session,
        task=tasks[1],
        code_repo_path=repo_full_name,
        commit_sha=head_sha,
        workflow_run_status="queued",
        last_run_at=datetime(2026, 3, 13, 8, 0, tzinfo=UTC),
    )
    second = await create_submission(
        async_session,
        candidate_session=second_session,
        task=tasks[1],
        code_repo_path=repo_full_name,
        commit_sha=head_sha,
        workflow_run_status="in_progress",
        last_run_at=datetime(2026, 3, 13, 8, 1, tzinfo=UTC),
    )
    await async_session.commit()

    result = await workflow_run.process_workflow_run_completed_event(
        async_session,
        payload=_workflow_payload(
            run_id=707001,
            repo_full_name=repo_full_name,
            head_sha=head_sha,
        ),
        delivery_id="delivery-ambiguous-fallback",
    )

    assert result.outcome == "unmatched"
    assert result.reason_code == "mapping_ambiguous_repo_head_sha"
    assert result.submission_id is None
    assert result.enqueued_artifact_parse is False

    await async_session.refresh(first)
    await async_session.refresh(second)
    assert first.workflow_run_id is None
    assert second.workflow_run_id is None
    assert first.workflow_run_status == "queued"
    assert second.workflow_run_status == "in_progress"

    jobs = (
        await async_session.execute(
            select(Job).where(
                Job.job_type == workflow_run.GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE
            )
        )
    ).scalars()
    assert list(jobs) == []
