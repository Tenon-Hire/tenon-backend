from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.shared.jobs.handlers import trial_cleanup as cleanup_handler
from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import (
    WORKSPACE_CLEANUP_STATUS_ARCHIVED,
    Workspace,
    WorkspaceGroup,
    _session_maker,
    create_candidate_session,
    create_talent_partner,
    create_trial,
    cs_repo,
    workspace_repo,
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
async def test_handle_trial_cleanup_processes_only_trial_owned_workspaces(
    async_session, monkeypatch
):
    talent_partner = await create_talent_partner(
        async_session, email="cleanup-owner@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    other_trial, _other_tasks = await create_trial(
        async_session,
        created_by=talent_partner,
        title="Other cleanup trial",
    )

    trial.status = "terminated"
    trial.terminated_at = datetime.now(UTC)
    trial.terminated_by_talent_partner_id = talent_partner.id
    await async_session.flush()

    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="cleanup-target@example.com",
        candidate_name="Cleanup Target",
        with_default_schedule=True,
    )
    legacy_candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="cleanup-legacy@example.com",
        candidate_name="Cleanup Legacy",
        with_default_schedule=True,
    )
    other_candidate_session = await create_candidate_session(
        async_session,
        trial=other_trial,
        invite_email="cleanup-other@example.com",
        candidate_name="Cleanup Other",
        with_default_schedule=True,
    )
    candidate_session.github_username = "octocat"
    legacy_candidate_session.github_username = "legacy-user"
    other_candidate_session.github_username = "other-user"

    created_at = datetime.now(UTC)
    target_group = await workspace_repo.create_workspace_group(
        async_session,
        candidate_session_id=candidate_session.id,
        workspace_key="coding",
        template_repo_full_name="org/template-repo",
        repo_full_name="org/cleanup-target",
        default_branch="main",
        base_template_sha="base-sha",
        created_at=created_at,
    )
    legacy_workspace = await workspace_repo.create_workspace(
        async_session,
        workspace_group_id=None,
        candidate_session_id=legacy_candidate_session.id,
        task_id=tasks[2].id,
        template_repo_full_name="org/template-repo",
        repo_full_name="org/cleanup-legacy",
        repo_id=5678,
        default_branch="main",
        base_template_sha="base-sha",
        created_at=created_at,
    )
    other_group = await workspace_repo.create_workspace_group(
        async_session,
        candidate_session_id=other_candidate_session.id,
        workspace_key="coding",
        template_repo_full_name="org/template-repo",
        repo_full_name="org/cleanup-other",
        default_branch="main",
        base_template_sha="base-sha",
        created_at=created_at,
    )
    await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=2,
        cutoff_at=created_at,
        cutoff_commit_sha="cutoff-sha",
        eval_basis_ref="refs/heads/main@cutoff",
        commit=False,
    )
    await cs_repo.create_day_audit_once(
        async_session,
        candidate_session_id=legacy_candidate_session.id,
        day_index=3,
        cutoff_at=created_at,
        cutoff_commit_sha="cutoff-sha-legacy",
        eval_basis_ref="refs/heads/main@cutoff-legacy",
        commit=False,
    )
    await async_session.commit()

    calls = {"remove": 0, "archive": 0, "delete": 0}
    target_repos = {target_group.repo_full_name, legacy_workspace.repo_full_name}

    class StubGithubClient:
        async def remove_collaborator(self, repo_full_name, github_username):
            calls["remove"] += 1
            assert repo_full_name in target_repos
            assert github_username in {"octocat", "legacy-user"}
            return {}

        async def archive_repo(self, repo_full_name):
            calls["archive"] += 1
            assert repo_full_name in target_repos
            return {"archived": True}

        async def delete_repo(self, repo_full_name):
            calls["delete"] += 1
            assert repo_full_name in target_repos
            return {}

    monkeypatch.setattr(
        cleanup_handler, "async_session_maker", _session_maker(async_session)
    )
    monkeypatch.setattr(
        cleanup_handler, "get_github_client", lambda: StubGithubClient()
    )

    result = await cleanup_handler.handle_trial_cleanup({"trialId": trial.id})

    assert result["status"] == "completed"
    assert result["trialId"] == trial.id
    assert result["candidateCount"] == 2
    assert result["processed"] == 2
    assert result["revoked"] == 2
    assert result["archived"] == 2
    assert result["deleted"] == 0
    assert result["alreadyCleaned"] == 0
    assert result["failed"] == 0

    stored_group = await async_session.get(WorkspaceGroup, target_group.id)
    assert stored_group is not None
    await async_session.refresh(stored_group)
    assert stored_group.cleanup_status == WORKSPACE_CLEANUP_STATUS_ARCHIVED
    assert stored_group.cleanup_attempted_at is not None
    assert stored_group.retention_expires_at is not None
    assert stored_group.cleaned_at is not None
    assert stored_group.access_revoked_at is not None
    assert stored_group.cleanup_error is None

    stored_legacy_workspace = await async_session.get(Workspace, legacy_workspace.id)
    assert stored_legacy_workspace is not None
    await async_session.refresh(stored_legacy_workspace)
    assert stored_legacy_workspace.cleanup_status == WORKSPACE_CLEANUP_STATUS_ARCHIVED
    assert stored_legacy_workspace.cleanup_attempted_at is not None
    assert stored_legacy_workspace.retention_expires_at is not None
    assert stored_legacy_workspace.cleaned_at is not None
    assert stored_legacy_workspace.access_revoked_at is not None
    assert stored_legacy_workspace.cleanup_error is None

    untouched_other_group = await async_session.get(WorkspaceGroup, other_group.id)
    assert untouched_other_group is not None
    await async_session.refresh(untouched_other_group)
    assert untouched_other_group.cleanup_status is None
    assert untouched_other_group.cleaned_at is None
    assert untouched_other_group.access_revoked_at is None

    second = await cleanup_handler.handle_trial_cleanup({"trialId": trial.id})
    assert second["status"] == "completed"
    assert second["alreadyCleaned"] == 2
    assert calls == {"remove": 2, "archive": 2, "delete": 0}
