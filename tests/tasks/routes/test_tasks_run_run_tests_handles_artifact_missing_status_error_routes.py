from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_run_tests_handles_artifact_missing_status_error(
    async_client, async_session, candidate_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="artifact@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await async_session.commit()

    class ErrorStatusRunner:
        async def dispatch_and_wait(self, **_kwargs):
            return ActionsRunResult(
                status="error",
                run_id=321,
                conclusion="success",
                passed=None,
                failed=None,
                total=None,
                stdout=None,
                stderr="Test results artifact missing or unreadable. Please re-run tests.",
                head_sha="sha321",
                html_url="https://example.com/run/321",
                raw={"artifact_error": "artifact_missing"},
            )

    class StubGithubClient:
        async def generate_repo_from_template(
            self, *, template_full_name, new_repo_name, owner=None, private=True
        ):
            return {
                "full_name": f"{owner}/{new_repo_name}",
                "id": 999,
                "default_branch": "main",
            }

        async def add_collaborator(self, *_a, **_k):
            return {"ok": True}

        async def get_branch(self, *_a, **_k):
            return {"commit": {"sha": "base"}}

        async def get_compare(self, *_a, **_k):
            return {}

    with override_dependencies(
        {
            candidate_submissions.get_actions_runner: lambda: ErrorStatusRunner(),
            candidate_submissions.get_github_client: lambda: StubGithubClient(),
        }
    ):
        headers = candidate_header_factory(cs)
        await async_client.post(
            f"/api/tasks/{tasks[1].id}/codespace/init",
            headers=headers,
            json={"githubUsername": "octocat"},
        )
        resp = await async_client.post(
            f"/api/tasks/{tasks[1].id}/run",
            headers=headers,
            json={},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "error"
    assert "artifact" in (data.get("stderr") or "").lower()
