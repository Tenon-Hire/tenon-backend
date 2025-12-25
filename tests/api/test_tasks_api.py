import json

import pytest
from sqlalchemy import delete, select

from app.api.routes.candidate import submissions as candidate_submissions
from app.domain import Submission, Task
from app.main import app
from app.services.sandbox_client import SandboxError, SandboxRunResult
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
    create_submission,
)


class StubSandboxClient:
    def __init__(self, result: SandboxRunResult):
        self._result = result

    async def run_tests(self, **_kwargs):
        return self._result


@pytest.mark.asyncio
async def test_submit_rejects_expired_session(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="expired@sim.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
        expires_in_days=-1,
    )

    task_id = tasks[0].id
    res = await async_client.post(
        f"/api/tasks/{task_id}/submit",
        headers={
            "x-candidate-token": cs.token,
            "x-candidate-session-id": str(cs.id),
        },
        json={"contentText": "should fail"},
    )
    assert res.status_code == 410


@pytest.mark.asyncio
async def test_submit_after_completion_returns_409(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="done@sim.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
    )

    # Seed submissions for all tasks to mark sim complete
    for task in tasks:
        await create_submission(
            async_session,
            candidate_session=cs,
            task=task,
            content_text="done",
        )
    await async_session.refresh(cs)

    task_id = tasks[-1].id
    res = await async_client.post(
        f"/api/tasks/{task_id}/submit",
        headers={
            "x-candidate-token": cs.token,
            "x-candidate-session-id": str(cs.id),
        },
        json={"contentText": "too late"},
    )
    assert res.status_code == 409
    assert res.json()["detail"] in {
        "Simulation already completed",
        "Task already submitted",
    }


@pytest.mark.asyncio
async def test_submit_returns_500_when_simulation_missing_tasks(
    async_client, async_session
):
    recruiter = await create_recruiter(async_session, email="notasks@sim.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )

    # Remove tasks to exercise guard
    await async_session.execute(delete(Task).where(Task.simulation_id == sim.id))
    await async_session.commit()

    res = await async_client.post(
        f"/api/tasks/{tasks[0].id}/submit",
        headers={
            "x-candidate-token": cs.token,
            "x-candidate-session-id": str(cs.id),
        },
        json={"contentText": "should error"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_submit_task_not_found(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="missingtask@sim.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )

    res = await async_client.post(
        "/api/tasks/999999/submit",
        headers={
            "x-candidate-token": cs.token,
            "x-candidate-session-id": str(cs.id),
        },
        json={"contentText": "no task"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_submit_task_from_other_simulation(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="cross@sim.com")
    sim_a, tasks_a = await create_simulation(async_session, created_by=recruiter)
    sim_b, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session, simulation=sim_b, status="in_progress"
    )

    # Use task from sim_a with session from sim_b -> 404
    res = await async_client.post(
        f"/api/tasks/{tasks_a[0].id}/submit",
        headers={
            "x-candidate-token": cs.token,
            "x-candidate-session-id": str(cs.id),
        },
        json={"contentText": "wrong sim"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_submit_unknown_task_type_errors(async_client, async_session):
    recruiter = await create_recruiter(async_session, email="unk@sim.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )

    # Manually insert a task with unsupported type
    res_tasks = await async_session.execute(
        select(Task).where(Task.simulation_id == sim.id).order_by(Task.day_index)
    )
    for t in res_tasks.scalars():
        await async_session.delete(t)
    await async_session.commit()

    bad_task = Task(
        simulation_id=sim.id,
        day_index=1,
        type="behavioral",
        title="Unknown type",
        description="N/A",
    )
    async_session.add(bad_task)
    await async_session.commit()
    await async_session.refresh(bad_task)

    res = await async_client.post(
        f"/api/tasks/{bad_task.id}/submit",
        headers={
            "x-candidate-token": cs.token,
            "x-candidate-session-id": str(cs.id),
        },
        json={"contentText": "unknown"},
    )
    assert res.status_code == 500


@pytest.mark.asyncio
async def test_submit_code_task_persists_sandbox_results(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="code-submit@sim.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )
    # Seed day 1 submission to unlock day 2 code task
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await async_session.commit()

    fake_result = SandboxRunResult(
        status="failed",
        passed=1,
        failed=2,
        total=3,
        stdout="prints",
        stderr="boom",
        duration_ms=None,
        raw=None,
    )
    app.dependency_overrides[candidate_submissions.get_sandbox_client] = (
        lambda: StubSandboxClient(fake_result)
    )

    headers = candidate_header_factory(cs.id, cs.token)
    resp = await async_client.post(
        f"/api/tasks/{tasks[1].id}/submit",
        headers=headers,
        json={"codeBlob": "print('hi')"},
    )

    app.dependency_overrides.pop(candidate_submissions.get_sandbox_client, None)

    assert resp.status_code == 201, resp.text
    sub = await async_session.get(Submission, resp.json()["submissionId"])
    assert sub.tests_passed == 1
    assert sub.tests_failed == 2
    assert sub.last_run_at is not None
    assert sub.test_output
    payload = json.loads(sub.test_output)
    assert payload["status"] == "failed"
    assert payload["passed"] == 1
    assert payload["failed"] == 2
    assert payload["total"] == 3
    assert payload["stdout"] == "prints"
    assert payload["stderr"] == "boom"
    assert payload["timeout"] is False


@pytest.mark.asyncio
async def test_submit_text_task_leaves_test_fields_null(
    async_client, async_session, candidate_header_factory
):
    recruiter = await create_recruiter(async_session, email="text-submit@sim.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )

    headers = candidate_header_factory(cs.id, cs.token)
    resp = await async_client.post(
        f"/api/tasks/{tasks[0].id}/submit",
        headers=headers,
        json={"contentText": "design answer"},
    )

    assert resp.status_code == 201, resp.text
    sub = await async_session.get(Submission, resp.json()["submissionId"])
    assert sub.tests_passed is None
    assert sub.tests_failed is None
    assert sub.test_output is None
    assert sub.last_run_at is None


@pytest.mark.asyncio
async def test_submit_code_task_sandbox_error_returns_502_no_submission(
    async_client, async_session, candidate_header_factory, sandbox_stubber
):
    recruiter = await create_recruiter(async_session, email="sandbox-err@sim.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )
    # seed day 1 to reach day 2 code task
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await async_session.commit()

    sandbox_stubber(error=SandboxError("boom"))

    headers = candidate_header_factory(cs.id, cs.token)
    resp = await async_client.post(
        f"/api/tasks/{tasks[1].id}/submit",
        headers=headers,
        json={"codeBlob": "print('hi')"},
    )

    assert resp.status_code == 502
    result = await async_session.execute(
        select(Submission).where(
            Submission.candidate_session_id == cs.id, Submission.task_id == tasks[1].id
        )
    )
    assert result.scalar_one_or_none() is None
