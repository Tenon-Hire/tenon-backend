import pytest

from app.api.routes.candidate import submissions as candidate_submissions
from app.domain.submissions.schemas import RunTestsRequest, SubmissionCreateRequest
from app.services.sandbox_client import SandboxError
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
    create_submission,
)


class RaisingSandboxClient:
    def __init__(self, exc: Exception):
        self._exc = exc

    async def run_tests(self, **_kwargs):
        raise self._exc


@pytest.mark.asyncio
async def test_submit_task_sandbox_error_returns_502(async_session):
    recruiter = await create_recruiter(async_session, email="err@sim.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )
    # Seed day 1 so day 2 (code) becomes current
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await async_session.commit()

    with pytest.raises(Exception) as excinfo:
        await candidate_submissions.submit_task(
            task_id=tasks[1].id,
            payload=SubmissionCreateRequest(codeBlob="print('x')"),
            x_candidate_token=cs.token,
            x_candidate_session_id=cs.id,
            db=async_session,
            sandbox_client=RaisingSandboxClient(SandboxError("boom")),
        )
    assert hasattr(excinfo.value, "status_code")
    assert excinfo.value.status_code == 502


@pytest.mark.asyncio
async def test_run_task_tests_sandbox_error_returns_502(async_session):
    recruiter = await create_recruiter(async_session, email="runerr@sim.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(
        async_session, simulation=sim, status="in_progress"
    )
    # Seed day 1 so day 2 is current for run
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await async_session.commit()

    with pytest.raises(Exception) as excinfo:
        await candidate_submissions.run_task_tests(
            task_id=tasks[1].id,
            payload=RunTestsRequest(codeBlob="print('x')"),
            db=async_session,
            sandbox_client=RaisingSandboxClient(SandboxError("boom")),
            x_candidate_token=cs.token,
            x_candidate_session_id=cs.id,
        )
    assert hasattr(excinfo.value, "status_code")
    assert excinfo.value.status_code == 502
