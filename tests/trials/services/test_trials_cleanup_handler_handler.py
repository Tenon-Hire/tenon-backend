from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared.jobs.handlers import (
    shared_jobs_handlers_trial_cleanup_handler as cleanup_handler,
)
from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )


def test_parse_trial_id_helper_variants():
    assert cleanup_handler._parse_trial_id({"trialId": True}) is None
    assert cleanup_handler._parse_trial_id({"trialId": "0"}) is None
    assert cleanup_handler._parse_trial_id({"trialId": "42"}) == 42


@pytest.mark.asyncio
async def test_handle_trial_cleanup_skips_invalid_payload():
    result = await cleanup_handler.handle_trial_cleanup({"trialId": "abc"})
    assert result["status"] == "skipped_invalid_payload"


@pytest.mark.asyncio
async def test_handle_trial_cleanup_trial_not_found(async_session, monkeypatch):
    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    result = await cleanup_handler.handle_trial_cleanup({"trialId": 999999})
    assert result == {"status": "trial_not_found", "trialId": 999999}


@pytest.mark.asyncio
async def test_handle_trial_cleanup_skips_when_not_terminated(
    async_session, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="cleanup-skip@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    await async_session.commit()

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    result = await cleanup_handler.handle_trial_cleanup({"trialId": trial.id})
    assert result == {
        "status": "skipped_not_terminated",
        "trialId": trial.id,
    }


@pytest.mark.asyncio
async def test_handle_trial_cleanup_noop_counts_trial_owned_workspaces(
    async_session, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="cleanup-noop@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    trial.status = "terminated"
    trial.terminated_at = datetime.now(UTC)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
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
    result = await cleanup_handler.handle_trial_cleanup({"trialId": trial.id})
    assert result["status"] == "noop"
    assert result["trialId"] == trial.id
    assert result["workspaceRepoCount"] == 1
    assert result["protectedTemplateRepoMatches"] == 1
