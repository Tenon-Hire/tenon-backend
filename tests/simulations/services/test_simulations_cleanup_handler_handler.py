from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.jobs.handlers import (
    shared_jobs_handlers_simulation_cleanup_handler as cleanup_handler,
)
from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from tests.shared.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )


def test_parse_simulation_id_helper_variants():
    assert cleanup_handler._parse_simulation_id({"simulationId": True}) is None
    assert cleanup_handler._parse_simulation_id({"simulationId": "0"}) is None
    assert cleanup_handler._parse_simulation_id({"simulationId": "42"}) == 42


@pytest.mark.asyncio
async def test_handle_simulation_cleanup_skips_invalid_payload():
    result = await cleanup_handler.handle_simulation_cleanup({"simulationId": "abc"})
    assert result["status"] == "skipped_invalid_payload"


@pytest.mark.asyncio
async def test_handle_simulation_cleanup_simulation_not_found(
    async_session, monkeypatch
):
    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    result = await cleanup_handler.handle_simulation_cleanup({"simulationId": 999999})
    assert result == {"status": "simulation_not_found", "simulationId": 999999}


@pytest.mark.asyncio
async def test_handle_simulation_cleanup_skips_when_not_terminated(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(async_session, email="cleanup-skip@test.com")
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    await async_session.commit()

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    result = await cleanup_handler.handle_simulation_cleanup(
        {"simulationId": simulation.id}
    )
    assert result == {
        "status": "skipped_not_terminated",
        "simulationId": simulation.id,
    }


@pytest.mark.asyncio
async def test_handle_simulation_cleanup_noop_counts_simulation_owned_workspaces(
    async_session, monkeypatch
):
    recruiter = await create_recruiter(async_session, email="cleanup-noop@test.com")
    simulation, tasks = await create_simulation(async_session, created_by=recruiter)
    simulation.status = "terminated"
    simulation.terminated_at = datetime.now(UTC)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        invite_email="cleanup-noop@example.com",
    )
    await async_session.commit()

    await workspace_repo.create_workspace(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=tasks[0].id,
        template_repo_full_name="org/template-repo",
        repo_full_name="org/template-repo",
        repo_id=12345,
        default_branch="main",
        base_template_sha="abc123",
        created_at=datetime.now(UTC),
    )

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    result = await cleanup_handler.handle_simulation_cleanup(
        {"simulationId": simulation.id}
    )
    assert result["status"] == "noop"
    assert result["simulationId"] == simulation.id
    assert result["workspaceRepoCount"] == 1
    assert result["protectedTemplateRepoMatches"] == 1
