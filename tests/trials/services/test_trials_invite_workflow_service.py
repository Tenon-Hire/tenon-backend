from __future__ import annotations

import logging
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.config import settings
from app.trials.services import (
    trials_services_trials_invite_workflow_service as invite_workflow,
)


class FakeDB:
    def __init__(self) -> None:
        self.rollback_calls = 0

    async def rollback(self) -> None:
        self.rollback_calls += 1


@pytest.mark.asyncio
async def test_invite_workflow_cleanup_helper_handles_missing_and_failing_delete_repo(
    caplog,
):
    caplog.set_level(logging.WARNING)

    await invite_workflow._cleanup_provisioned_repos(object(), ["org/repo"])

    class GithubStub:
        def __init__(self) -> None:
            self.deleted_repos: list[str] = []

        async def delete_repo(self, repo_full_name: str):
            self.deleted_repos.append(repo_full_name)
            raise RuntimeError("boom")

    github_client = GithubStub()
    await invite_workflow._cleanup_provisioned_repos(github_client, ["org/repo"])

    assert github_client.deleted_repos == ["org/repo"]
    assert any(
        record.message == "github_workspace_preprovision_cleanup_failed"
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_invite_workflow_re_raises_unrelated_typeerror_from_require(monkeypatch):
    async def _raise_typeerror(*_args, **_kwargs):
        raise TypeError("unexpected signature mismatch")

    monkeypatch.setattr(
        invite_workflow.sim_service,
        "require_owned_trial_with_tasks",
        _raise_typeerror,
    )

    with pytest.raises(TypeError, match="unexpected signature mismatch"):
        await invite_workflow.create_candidate_invite_workflow(
            db=object(),
            trial_id=1,
            payload=SimpleNamespace(inviteEmail="a@b.com", candidateName="Name"),
            user_id=2,
            email_service=object(),
            github_client=object(),
            now=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_invite_workflow_re_raises_unrelated_typeerror_from_lock(monkeypatch):
    async def _require_owned(*_args, **_kwargs):
        return SimpleNamespace(id=1, token="tok"), []

    async def _raise_typeerror(*_args, **_kwargs):
        raise TypeError("lock call failed")

    monkeypatch.setattr(
        invite_workflow.sim_service,
        "require_owned_trial_with_tasks",
        _require_owned,
    )
    monkeypatch.setattr(
        invite_workflow.sim_service,
        "require_trial_invitable",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        invite_workflow.sim_service,
        "lock_active_scenario_for_invites",
        _raise_typeerror,
    )

    with pytest.raises(TypeError, match="lock call failed"):
        await invite_workflow.create_candidate_invite_workflow(
            db=object(),
            trial_id=1,
            payload=SimpleNamespace(inviteEmail="a@b.com", candidateName="Name"),
            user_id=2,
            email_service=object(),
            github_client=object(),
            now=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_invite_workflow_cleans_up_created_repo_when_email_send_fails(
    monkeypatch,
):
    db = FakeDB()
    trial = SimpleNamespace(id=5, title="Trial", role="Engineer")
    scenario_version = SimpleNamespace(id=9)
    candidate_session = SimpleNamespace(
        id=77,
        token="tok-77",
        _invite_newly_created=True,
    )
    payload = SimpleNamespace(inviteEmail="jane@example.com", candidateName="Jane Doe")

    class GithubStub:
        def __init__(self) -> None:
            self.deleted_repos: list[str] = []

        async def delete_repo(self, repo_full_name: str):
            self.deleted_repos.append(repo_full_name)

    github_client = GithubStub()

    async def _require_owned(*_args, **_kwargs):
        return trial, [SimpleNamespace(id=1, day_index=2, type="code")]

    async def _lock_active(*_args, **_kwargs):
        return scenario_version

    async def _create_or_resend(*_args, **_kwargs):
        return candidate_session, "created"

    async def _preprovision(*_args, **_kwargs):
        return ["winoe-ai-repos/winoe-ws-77"]

    async def _send_invite_email(*_args, **_kwargs):
        raise RuntimeError("email provider down")

    monkeypatch.setattr(
        invite_workflow.sim_service,
        "require_owned_trial_with_tasks",
        _require_owned,
    )
    monkeypatch.setattr(
        invite_workflow.sim_service,
        "require_trial_invitable",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        invite_workflow.sim_service,
        "lock_active_scenario_for_invites",
        _lock_active,
    )
    monkeypatch.setattr(
        invite_workflow.sim_service,
        "create_or_resend_invite",
        _create_or_resend,
    )
    monkeypatch.setattr(
        invite_workflow.invite_preprovision,
        "preprovision_workspaces",
        _preprovision,
    )
    monkeypatch.setattr(
        invite_workflow.notification_service,
        "send_invite_email",
        _send_invite_email,
    )
    monkeypatch.setattr(settings.github, "GITHUB_ORG", "winoe-ai-repos")
    monkeypatch.setattr(settings.github, "GITHUB_REPO_PREFIX", "winoe-ws-")

    with pytest.raises(RuntimeError, match="email provider down"):
        await invite_workflow.create_candidate_invite_workflow(
            db=db,
            trial_id=5,
            payload=payload,
            user_id=9,
            email_service=object(),
            github_client=github_client,
            now=datetime.now(UTC),
        )

    assert db.rollback_calls == 1
    assert github_client.deleted_repos == ["winoe-ai-repos/winoe-ws-77"]


@pytest.mark.asyncio
async def test_invite_workflow_cleans_up_created_repo_when_preprovision_fails(
    monkeypatch,
):
    db = FakeDB()
    trial = SimpleNamespace(id=6, title="Trial", role="Engineer")
    scenario_version = SimpleNamespace(id=10)
    candidate_session = SimpleNamespace(
        id=78,
        token="tok-78",
        _invite_newly_created=True,
    )
    payload = SimpleNamespace(inviteEmail="jane@example.com", candidateName="Jane Doe")

    class GithubStub:
        def __init__(self) -> None:
            self.deleted_repos: list[str] = []

        async def delete_repo(self, repo_full_name: str):
            self.deleted_repos.append(repo_full_name)

    github_client = GithubStub()

    async def _require_owned(*_args, **_kwargs):
        return trial, [SimpleNamespace(id=1, day_index=2, type="code")]

    async def _lock_active(*_args, **_kwargs):
        return scenario_version

    async def _create_or_resend(*_args, **_kwargs):
        return candidate_session, "created"

    async def _preprovision(*_args, **_kwargs):
        exc = RuntimeError("bootstrap failed")
        exc.provisioned_repo_full_names = ("winoe-ai-repos/winoe-ws-78",)
        raise exc

    monkeypatch.setattr(
        invite_workflow.sim_service,
        "require_owned_trial_with_tasks",
        _require_owned,
    )
    monkeypatch.setattr(
        invite_workflow.sim_service,
        "require_trial_invitable",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        invite_workflow.sim_service,
        "lock_active_scenario_for_invites",
        _lock_active,
    )
    monkeypatch.setattr(
        invite_workflow.sim_service,
        "create_or_resend_invite",
        _create_or_resend,
    )
    monkeypatch.setattr(
        invite_workflow.invite_preprovision,
        "preprovision_workspaces",
        _preprovision,
    )
    monkeypatch.setattr(settings.github, "GITHUB_ORG", "winoe-ai-repos")
    monkeypatch.setattr(settings.github, "GITHUB_REPO_PREFIX", "winoe-ws-")

    with pytest.raises(RuntimeError, match="bootstrap failed"):
        await invite_workflow.create_candidate_invite_workflow(
            db=db,
            trial_id=6,
            payload=payload,
            user_id=9,
            email_service=object(),
            github_client=github_client,
            now=datetime.now(UTC),
        )

    assert db.rollback_calls == 1
    assert github_client.deleted_repos == ["winoe-ai-repos/winoe-ws-78"]


@pytest.mark.asyncio
async def test_invite_workflow_handles_none_cleanup_targets_from_preprovision(
    monkeypatch,
):
    db = FakeDB()
    trial = SimpleNamespace(id=7, title="Trial", role="Engineer")
    scenario_version = SimpleNamespace(id=11)
    candidate_session = SimpleNamespace(
        id=79,
        token="tok-79",
        _invite_newly_created=True,
    )
    payload = SimpleNamespace(inviteEmail="jane@example.com", candidateName="Jane Doe")

    class GithubStub:
        def __init__(self) -> None:
            self.deleted_repos: list[str] = []

        async def delete_repo(self, repo_full_name: str):
            self.deleted_repos.append(repo_full_name)

    github_client = GithubStub()

    async def _require_owned(*_args, **_kwargs):
        return trial, [SimpleNamespace(id=1, day_index=2, type="code")]

    async def _lock_active(*_args, **_kwargs):
        return scenario_version

    async def _create_or_resend(*_args, **_kwargs):
        return candidate_session, "created"

    async def _preprovision(*_args, **_kwargs):
        return None

    async def _send_invite_email(*_args, **_kwargs):
        raise RuntimeError("email provider down")

    monkeypatch.setattr(
        invite_workflow.sim_service,
        "require_owned_trial_with_tasks",
        _require_owned,
    )
    monkeypatch.setattr(
        invite_workflow.sim_service,
        "require_trial_invitable",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        invite_workflow.sim_service,
        "lock_active_scenario_for_invites",
        _lock_active,
    )
    monkeypatch.setattr(
        invite_workflow.sim_service,
        "create_or_resend_invite",
        _create_or_resend,
    )
    monkeypatch.setattr(
        invite_workflow.invite_preprovision,
        "preprovision_workspaces",
        _preprovision,
    )
    monkeypatch.setattr(
        invite_workflow.notification_service,
        "send_invite_email",
        _send_invite_email,
    )
    monkeypatch.setattr(settings.github, "GITHUB_ORG", "winoe-ai-repos")
    monkeypatch.setattr(settings.github, "GITHUB_REPO_PREFIX", "winoe-ws-")

    with pytest.raises(RuntimeError, match="email provider down"):
        await invite_workflow.create_candidate_invite_workflow(
            db=db,
            trial_id=7,
            payload=payload,
            user_id=9,
            email_service=object(),
            github_client=github_client,
            now=datetime.now(UTC),
        )

    assert db.rollback_calls == 1
    assert github_client.deleted_repos == []
