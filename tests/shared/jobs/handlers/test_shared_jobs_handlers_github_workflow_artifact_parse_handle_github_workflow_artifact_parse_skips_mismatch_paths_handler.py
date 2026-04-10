from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_github_workflow_artifact_parse_utils import *


@pytest.mark.asyncio
async def test_handle_github_workflow_artifact_parse_skips_mismatch_paths(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session,
        email="parse-handler-mismatch@winoe.dev",
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
        code_repo_path="acme/parse-handler-repo",
        workflow_run_id="321",
    )
    await async_session.commit()

    session_maker = async_sessionmaker(
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )
    monkeypatch.setattr(parse_handler, "async_session_maker", session_maker)

    candidate_mismatch = await parse_handler.handle_github_workflow_artifact_parse(
        {
            "submissionId": submission.id,
            "candidateSessionId": candidate_session.id + 999,
            "taskId": tasks[1].id,
            "repoFullName": "acme/parse-handler-repo",
            "workflowRunId": 321,
        }
    )
    assert candidate_mismatch["status"] == "skipped_candidate_session_mismatch"

    task_mismatch = await parse_handler.handle_github_workflow_artifact_parse(
        {
            "submissionId": submission.id,
            "candidateSessionId": candidate_session.id,
            "taskId": tasks[1].id + 999,
            "repoFullName": "acme/parse-handler-repo",
            "workflowRunId": 321,
        }
    )
    assert task_mismatch["status"] == "skipped_task_mismatch"

    run_mismatch = await parse_handler.handle_github_workflow_artifact_parse(
        {
            "submissionId": submission.id,
            "candidateSessionId": candidate_session.id,
            "taskId": tasks[1].id,
            "repoFullName": "acme/parse-handler-repo",
            "workflowRunId": 999,
        }
    )
    assert run_mismatch["status"] == "skipped_workflow_run_mismatch"
