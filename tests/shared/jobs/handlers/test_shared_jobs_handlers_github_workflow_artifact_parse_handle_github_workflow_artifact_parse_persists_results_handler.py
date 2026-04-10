from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_github_workflow_artifact_parse_utils import *


@pytest.mark.asyncio
async def test_handle_github_workflow_artifact_parse_persists_results(
    async_session,
    monkeypatch,
):
    talent_partner = await create_talent_partner(
        async_session, email="parse-handler@winoe.dev"
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
    workspace = Workspace(
        candidate_session_id=candidate_session.id,
        task_id=tasks[1].id,
        template_repo_full_name="acme/template-repo",
        repo_full_name="acme/parse-handler-repo",
        created_at=datetime.now(UTC),
    )
    async_session.add(workspace)
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
            assert run_id == 321
            return ActionsRunResult(
                status="passed",
                run_id=321,
                conclusion="success",
                passed=12,
                failed=0,
                total=12,
                stdout="ok",
                stderr=None,
                head_sha="abc321",
                html_url="https://example.test/runs/321",
                raw={"summary": {"passed": 12, "failed": 0}},
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
            "workflowRunId": 321,
            "workflowRunAttempt": 2,
            "workflowCompletedAt": "2026-03-13T14:00:00Z",
        }
    )

    assert result["status"] == "parsed_and_persisted"

    await async_session.refresh(submission)
    await async_session.refresh(workspace)
    assert submission.workflow_run_id == "321"
    assert submission.workflow_run_attempt == 2
    assert submission.workflow_run_status == "completed"
    assert submission.workflow_run_conclusion == "success"
    assert submission.tests_passed == 12
    assert submission.tests_failed == 0
    assert submission.commit_sha == "abc321"
    assert submission.test_output is not None
    parsed_output = json.loads(submission.test_output)
    assert parsed_output["runId"] == 321
    assert parsed_output["passed"] == 12
    assert parsed_output["failed"] == 0

    assert workspace.last_workflow_run_id == "321"
    assert workspace.last_workflow_conclusion == "success"
    assert workspace.latest_commit_sha == "abc321"
    assert workspace.last_test_summary_json is not None
