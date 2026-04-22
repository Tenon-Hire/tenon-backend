from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.shared.database.shared_database_models_model import Workspace
from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_run_routes as candidate_submissions,
)
from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_run_task_tests_persists_running_result(
    async_client, async_session, candidate_header_factory, override_dependencies
):
    talent_partner = await create_talent_partner(
        async_session, email="running-result@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=trial,
        status="in_progress",
        with_default_schedule=True,
    )
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    workspace = await workspace_repo.create_workspace(
        async_session,
        candidate_session_id=cs.id,
        task_id=tasks[1].id,
        template_repo_full_name=tasks[1].template_repo or "org/template",
        repo_full_name="org/candidate-running-result",
        repo_id=4242,
        default_branch="main",
        base_template_sha="base-sha",
        created_at=datetime.now(UTC),
    )
    await async_session.commit()

    class RunningRunner:
        async def dispatch_and_wait(self, **_kwargs):
            return ActionsRunResult(
                status="running",
                run_id=202,
                conclusion=None,
                passed=None,
                failed=None,
                total=None,
                stdout=None,
                stderr=None,
                head_sha="sha202",
                html_url="https://example.com/run/202",
                raw=None,
            )

    with override_dependencies(
        {
            candidate_submissions.get_actions_runner: lambda: RunningRunner(),
        }
    ):
        headers = candidate_header_factory(cs)
        resp = await async_client.post(
            f"/api/tasks/{tasks[1].id}/run",
            headers=headers,
            json={},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["runId"] == 202
    assert data["status"] == "running"

    refreshed = (
        await async_session.execute(
            select(Workspace).where(Workspace.id == workspace.id)
        )
    ).scalar_one()
    assert refreshed.last_workflow_run_id == "202"
    assert refreshed.last_workflow_conclusion is None
    assert refreshed.latest_commit_sha == "sha202"
