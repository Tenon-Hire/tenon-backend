from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_github_workflow_artifact_parse_utils import *


@pytest.mark.asyncio
async def test_handle_github_workflow_artifact_parse_sets_last_run_when_timestamp_missing(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session,
        email="parse-handler-last-run@winoe.dev",
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
        workflow_run_id=None,
        last_run_at=None,
    )
    await async_session.commit()

    session_maker = async_sessionmaker(
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )
    monkeypatch.setattr(parse_handler, "async_session_maker", session_maker)

    class StubRunner:
        async def fetch_run_result(self, *, repo_full_name: str, run_id: int):
            assert repo_full_name == "acme/parse-handler-repo"
            assert run_id == 322
            return ActionsRunResult(
                status="passed",
                run_id=322,
                conclusion=None,
                passed=3,
                failed=0,
                total=3,
                stdout="ok",
                stderr=None,
                head_sha="",
                html_url="https://example.test/runs/322",
                raw={"summary": {"passed": 3, "failed": 0}},
            )

    class StubGithubClient:
        async def aclose(self):
            return None

    monkeypatch.setattr(
        parse_handler,
        "_build_actions_runner",
        lambda: (StubRunner(), StubGithubClient()),
    )

    result = await parse_handler.handle_github_workflow_artifact_parse(
        {
            "submissionId": submission.id,
            "candidateSessionId": candidate_session.id,
            "taskId": tasks[1].id,
            "repoFullName": "acme/parse-handler-repo",
            "workflowRunId": 322,
        }
    )

    assert result["status"] == "parsed_and_persisted"
    await async_session.refresh(submission)
    assert submission.workflow_run_status == "completed"
    assert submission.workflow_run_conclusion is None
    assert submission.workflow_run_completed_at is None
    assert submission.last_run_at is not None


@pytest.mark.asyncio
async def test_handle_github_workflow_artifact_parse_preserves_existing_last_run_when_timestamp_missing(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session,
        email="parse-handler-last-run-existing@winoe.dev",
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        with_default_schedule=True,
    )
    existing_last_run_at = datetime(2026, 3, 27, 10, 0, tzinfo=UTC)
    submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks[1],
        code_repo_path="acme/parse-handler-repo-existing",
        workflow_run_id=None,
        last_run_at=existing_last_run_at,
    )
    await async_session.commit()

    session_maker = async_sessionmaker(
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )
    monkeypatch.setattr(parse_handler, "async_session_maker", session_maker)

    class StubRunner:
        async def fetch_run_result(self, *, repo_full_name: str, run_id: int):
            assert repo_full_name == "acme/parse-handler-repo-existing"
            assert run_id == 323
            return ActionsRunResult(
                status="passed",
                run_id=323,
                conclusion=None,
                passed=1,
                failed=0,
                total=1,
                stdout="ok",
                stderr=None,
                head_sha="",
                html_url="https://example.test/runs/323",
                raw={"summary": {"passed": 1, "failed": 0}},
            )

    class StubGithubClient:
        async def aclose(self):
            return None

    monkeypatch.setattr(
        parse_handler,
        "_build_actions_runner",
        lambda: (StubRunner(), StubGithubClient()),
    )

    result = await parse_handler.handle_github_workflow_artifact_parse(
        {
            "submissionId": submission.id,
            "candidateSessionId": candidate_session.id,
            "taskId": tasks[1].id,
            "repoFullName": "acme/parse-handler-repo-existing",
            "workflowRunId": 323,
        }
    )

    assert result["status"] == "parsed_and_persisted"
    await async_session.refresh(submission)
    assert submission.workflow_run_completed_at is None
    observed_last_run_at = submission.last_run_at
    assert observed_last_run_at is not None
    if observed_last_run_at.tzinfo is None:
        observed_last_run_at = observed_last_run_at.replace(tzinfo=UTC)
    assert observed_last_run_at == existing_last_run_at
