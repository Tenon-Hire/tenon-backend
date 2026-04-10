from __future__ import annotations

import pytest

from tests.integrations.github.webhooks.handlers.integrations_github_webhooks_workflow_run_handler_utils import *


@pytest.mark.asyncio
async def test_exact_workflow_run_id_match_takes_precedence_over_fallback(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="webhook-priority@winoe.dev"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)

    primary_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="webhook-priority-primary@winoe.dev",
        with_default_schedule=True,
    )
    fallback_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="webhook-priority-fallback@winoe.dev",
        with_default_schedule=True,
    )

    repo_full_name = "acme/preference-repo"
    run_id = 444101
    head_sha = "head-sha-precedence"

    direct_match = await create_submission(
        async_session,
        candidate_session=primary_session,
        task=tasks[1],
        code_repo_path=repo_full_name,
        workflow_run_id=str(run_id),
        workflow_run_status="queued",
        commit_sha="old-sha",
        last_run_at=datetime(2026, 3, 13, 8, 0, tzinfo=UTC),
    )
    fallback_candidate = await create_submission(
        async_session,
        candidate_session=fallback_session,
        task=tasks[1],
        code_repo_path=repo_full_name,
        commit_sha=head_sha,
        workflow_run_status="queued",
        last_run_at=datetime(2026, 3, 13, 8, 5, tzinfo=UTC),
    )

    workspace = Workspace(
        candidate_session_id=primary_session.id,
        task_id=tasks[1].id,
        template_repo_full_name="acme/template",
        repo_full_name=repo_full_name,
        latest_commit_sha="old-workspace-sha",
        created_at=datetime.now(UTC),
    )
    async_session.add(workspace)
    await async_session.commit()

    result = await workflow_run.process_workflow_run_completed_event(
        async_session,
        payload=_workflow_payload(
            run_id=run_id,
            repo_full_name=repo_full_name,
            head_sha=head_sha,
            run_attempt=2,
        ),
        delivery_id="delivery-priority",
    )

    assert result.outcome == "updated_status"
    assert result.reason_code == "matched_by_workflow_run_id"
    assert result.submission_id == direct_match.id
    assert result.workflow_run_id == run_id
    assert result.enqueued_artifact_parse is True

    await async_session.refresh(direct_match)
    await async_session.refresh(fallback_candidate)
    await async_session.refresh(workspace)

    assert direct_match.workflow_run_id == str(run_id)
    assert direct_match.workflow_run_status == "completed"
    assert direct_match.workflow_run_attempt == 2
    assert direct_match.workflow_run_conclusion == "success"
    assert direct_match.commit_sha == head_sha
    assert workspace.last_workflow_run_id == str(run_id)
    assert workspace.last_workflow_conclusion == "success"
    assert workspace.latest_commit_sha == head_sha

    assert fallback_candidate.workflow_run_id is None
    assert fallback_candidate.workflow_run_status == "queued"
    assert fallback_candidate.commit_sha == head_sha

    jobs = (
        await async_session.execute(
            select(Job).where(
                Job.job_type == workflow_run.GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE
            )
        )
    ).scalars()
    assert len(list(jobs)) == 1
