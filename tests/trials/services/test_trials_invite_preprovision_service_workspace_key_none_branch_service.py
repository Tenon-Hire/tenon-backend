from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.trials.services import (
    trials_services_trials_invite_preprovision_service as preprovision_service,
)


@pytest.mark.asyncio
async def test_preprovision_workspaces_skips_processed_key_tracking_when_key_missing(
    monkeypatch,
):
    captured_calls: list[dict] = []

    async def _ensure_workspace(
        _db,
        *,
        candidate_session,
        trial,
        scenario_version,
        task,
        github_client,
        github_username,
        repo_prefix,
        destination_owner,
        now,
        workspace_resolution=None,
        commit=True,
        hydrate_precommit_bundle=True,
        bootstrap_empty_repo=False,
    ):
        captured_calls.append(
            {
                "candidate_session_id": candidate_session.id,
                "trial_id": trial.id,
                "scenario_version_id": scenario_version.id,
                "task_id": task.id,
                "github_username": github_username,
                "destination_owner": destination_owner,
                "workspace_resolution": workspace_resolution,
                "commit": commit,
                "hydrate_precommit_bundle": hydrate_precommit_bundle,
                "bootstrap_empty_repo": bootstrap_empty_repo,
            }
        )

    monkeypatch.setattr(
        preprovision_service.settings.github,
        "GITHUB_REPO_PREFIX",
        "winoe",
    )
    monkeypatch.setattr(
        preprovision_service.settings.github, "GITHUB_ORG", "fallback-org"
    )
    monkeypatch.setattr(
        preprovision_service, "resolve_workspace_key_for_task", lambda _t: None
    )
    monkeypatch.setattr(
        preprovision_service.submission_service,
        "ensure_workspace",
        _ensure_workspace,
    )

    candidate_session = SimpleNamespace(id=42, trial_id=7, github_username="octocat")
    tasks = [SimpleNamespace(id=501, day_index=2, type="code", template_repo=None)]

    await preprovision_service.preprovision_workspaces(
        db=object(),
        candidate_session=candidate_session,
        trial=SimpleNamespace(id=7),
        scenario_version=SimpleNamespace(id=11),
        tasks=tasks,
        github_client=object(),
        now=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
        fresh_candidate_session=True,
    )

    assert len(captured_calls) == 1
    assert captured_calls[0]["task_id"] == 501
    assert captured_calls[0]["destination_owner"] == "fallback-org"
    assert captured_calls[0]["github_username"] == "octocat"
    assert captured_calls[0]["workspace_resolution"] is None
    assert captured_calls[0]["commit"] is False
    assert captured_calls[0]["hydrate_precommit_bundle"] is False
    assert captured_calls[0]["bootstrap_empty_repo"] is True


@pytest.mark.asyncio
async def test_preprovision_workspaces_skips_when_github_username_missing(
    monkeypatch,
):
    captured_calls: list[dict] = []

    async def _ensure_workspace(*_args, **_kwargs):
        captured_calls.append({"called": True})

    monkeypatch.setattr(
        preprovision_service.settings.github,
        "GITHUB_REPO_PREFIX",
        "winoe",
    )
    monkeypatch.setattr(
        preprovision_service.settings.github,
        "GITHUB_ORG",
        "fallback-org",
    )
    monkeypatch.setattr(
        preprovision_service, "resolve_workspace_key_for_task", lambda _t: "coding"
    )
    monkeypatch.setattr(
        preprovision_service.submission_service,
        "ensure_workspace",
        _ensure_workspace,
    )

    candidate_session = SimpleNamespace(id=42, trial_id=7, github_username=None)
    tasks = [SimpleNamespace(id=501, day_index=2, type="code", template_repo=None)]

    result = await preprovision_service.preprovision_workspaces(
        db=object(),
        candidate_session=candidate_session,
        trial=SimpleNamespace(id=7),
        scenario_version=SimpleNamespace(id=11),
        tasks=tasks,
        github_client=object(),
        now=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
        fresh_candidate_session=True,
    )

    assert result == []
    assert captured_calls == []


@pytest.mark.asyncio
async def test_preprovision_workspaces_returns_only_new_repos_for_cleanup(
    monkeypatch,
):
    captured_calls: list[dict] = []

    async def _ensure_workspace(
        _db,
        *,
        candidate_session,
        trial,
        scenario_version,
        task,
        github_client,
        github_username,
        repo_prefix,
        destination_owner,
        now,
        workspace_resolution=None,
        commit=True,
        hydrate_precommit_bundle=True,
        bootstrap_empty_repo=False,
    ):
        workspace = SimpleNamespace(
            repo_full_name=(
                "fallback-org/winoe-reused"
                if task.id == 501
                else "fallback-org/winoe-new"
            )
        )
        if task.id == 502:
            workspace._provisioned_repo_created = True
        captured_calls.append(
            {
                "task_id": task.id,
                "workspace_resolution": workspace_resolution,
                "repo_full_name": workspace.repo_full_name,
            }
        )
        return workspace

    monkeypatch.setattr(
        preprovision_service.settings.github,
        "GITHUB_REPO_PREFIX",
        "winoe",
    )
    monkeypatch.setattr(
        preprovision_service.settings.github,
        "GITHUB_ORG",
        "fallback-org",
    )

    def _resolve_workspace_key(task):
        return None if task.id == 501 else "coding"

    monkeypatch.setattr(
        preprovision_service, "resolve_workspace_key_for_task", _resolve_workspace_key
    )
    monkeypatch.setattr(
        preprovision_service.submission_service,
        "ensure_workspace",
        _ensure_workspace,
    )

    candidate_session = SimpleNamespace(id=42, trial_id=7, github_username="octocat")
    tasks = [
        SimpleNamespace(id=501, day_index=2, type="code", template_repo=None),
        SimpleNamespace(id=502, day_index=3, type="code", template_repo=None),
    ]

    result = await preprovision_service.preprovision_workspaces(
        db=object(),
        candidate_session=candidate_session,
        trial=SimpleNamespace(id=7),
        scenario_version=SimpleNamespace(id=11),
        tasks=tasks,
        github_client=object(),
        now=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
        fresh_candidate_session=True,
    )

    assert len(captured_calls) == 2
    assert result == ["fallback-org/winoe-new"]


@pytest.mark.asyncio
async def test_preprovision_workspaces_skips_duplicate_workspace_key(
    monkeypatch,
):
    captured_calls: list[int] = []

    async def _ensure_workspace(
        _db,
        *,
        candidate_session,
        trial,
        scenario_version,
        task,
        github_client,
        github_username,
        repo_prefix,
        destination_owner,
        now,
        workspace_resolution=None,
        commit=True,
        hydrate_precommit_bundle=True,
        bootstrap_empty_repo=False,
    ):
        captured_calls.append(task.id)
        return SimpleNamespace(repo_full_name=f"fallback-org/winoe-{task.id}")

    monkeypatch.setattr(
        preprovision_service.settings.github,
        "GITHUB_REPO_PREFIX",
        "winoe",
    )
    monkeypatch.setattr(
        preprovision_service.settings.github,
        "GITHUB_ORG",
        "fallback-org",
    )
    monkeypatch.setattr(
        preprovision_service, "resolve_workspace_key_for_task", lambda _t: "coding"
    )
    monkeypatch.setattr(
        preprovision_service.submission_service,
        "ensure_workspace",
        _ensure_workspace,
    )

    candidate_session = SimpleNamespace(id=42, trial_id=7, github_username="octocat")
    tasks = [
        SimpleNamespace(id=501, day_index=2, type="code", template_repo=None),
        SimpleNamespace(id=502, day_index=3, type="code", template_repo=None),
    ]

    result = await preprovision_service.preprovision_workspaces(
        db=object(),
        candidate_session=candidate_session,
        trial=SimpleNamespace(id=7),
        scenario_version=SimpleNamespace(id=11),
        tasks=tasks,
        github_client=object(),
        now=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
        fresh_candidate_session=True,
    )

    assert captured_calls == [501]
    assert result == []


@pytest.mark.asyncio
async def test_preprovision_workspaces_attaches_cleanup_targets_on_error(
    monkeypatch,
):
    created_repos: list[str] = []

    async def _ensure_workspace(
        _db,
        *,
        candidate_session,
        trial,
        scenario_version,
        task,
        github_client,
        github_username,
        repo_prefix,
        destination_owner,
        now,
        workspace_resolution=None,
        commit=True,
        hydrate_precommit_bundle=True,
        bootstrap_empty_repo=False,
    ):
        repo_full_name = f"fallback-org/winoe-{task.id}"
        created_repos.append(repo_full_name)
        if task.id == 502:
            raise preprovision_service.GithubError("boom", status_code=403)
        return SimpleNamespace(
            repo_full_name=repo_full_name, _provisioned_repo_created=True
        )

    monkeypatch.setattr(
        preprovision_service.settings.github,
        "GITHUB_REPO_PREFIX",
        "winoe",
    )
    monkeypatch.setattr(
        preprovision_service.settings.github,
        "GITHUB_ORG",
        "fallback-org",
    )
    monkeypatch.setattr(
        preprovision_service, "resolve_workspace_key_for_task", lambda _t: None
    )
    monkeypatch.setattr(
        preprovision_service.submission_service,
        "ensure_workspace",
        _ensure_workspace,
    )

    candidate_session = SimpleNamespace(id=42, trial_id=7, github_username="octocat")
    tasks = [
        SimpleNamespace(id=501, day_index=2, type="code", template_repo=None),
        SimpleNamespace(id=502, day_index=3, type="code", template_repo=None),
    ]

    with pytest.raises(preprovision_service.GithubError) as excinfo:
        await preprovision_service.preprovision_workspaces(
            db=object(),
            candidate_session=candidate_session,
            trial=SimpleNamespace(id=7),
            scenario_version=SimpleNamespace(id=11),
            tasks=tasks,
            github_client=object(),
            now=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
            fresh_candidate_session=True,
        )

    assert created_repos == [
        "fallback-org/winoe-501",
        "fallback-org/winoe-502",
    ]
    assert excinfo.value.provisioned_repo_full_names == ("fallback-org/winoe-501",)


@pytest.mark.asyncio
async def test_preprovision_workspaces_reraises_github_error_for_workspace_key(
    monkeypatch,
):
    captured_calls: list[dict] = []

    async def _ensure_workspace(
        _db,
        *,
        candidate_session,
        trial,
        scenario_version,
        task,
        github_client,
        github_username,
        repo_prefix,
        destination_owner,
        now,
        workspace_resolution=None,
        commit=True,
        hydrate_precommit_bundle=True,
        bootstrap_empty_repo=False,
    ):
        captured_calls.append(
            {
                "candidate_session_id": candidate_session.id,
                "trial_id": trial.id,
                "scenario_version_id": scenario_version.id,
                "task_id": task.id,
                "github_username": github_username,
                "destination_owner": destination_owner,
                "workspace_resolution": workspace_resolution,
                "commit": commit,
                "hydrate_precommit_bundle": hydrate_precommit_bundle,
                "bootstrap_empty_repo": bootstrap_empty_repo,
            }
        )
        raise preprovision_service.GithubError("boom", status_code=403)

    monkeypatch.setattr(
        preprovision_service.settings.github,
        "GITHUB_REPO_PREFIX",
        "winoe",
    )
    monkeypatch.setattr(
        preprovision_service.settings.github,
        "GITHUB_ORG",
        "winoe-ai-repos",
    )
    monkeypatch.setattr(
        preprovision_service, "resolve_workspace_key_for_task", lambda _t: "coding"
    )
    monkeypatch.setattr(
        preprovision_service.submission_service,
        "ensure_workspace",
        _ensure_workspace,
    )

    candidate_session = SimpleNamespace(id=42, trial_id=7, github_username="octocat")
    task = SimpleNamespace(
        id=501,
        day_index=2,
        type="code",
        template_repo=None,
    )

    with pytest.raises(preprovision_service.GithubError):
        await preprovision_service.preprovision_workspaces(
            db=object(),
            candidate_session=candidate_session,
            trial=SimpleNamespace(id=7),
            scenario_version=SimpleNamespace(id=11),
            tasks=[task],
            github_client=object(),
            now=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
            fresh_candidate_session=True,
        )

    assert len(captured_calls) == 1
    assert captured_calls[0]["destination_owner"] == "winoe-ai-repos"
    assert captured_calls[0]["github_username"] == "octocat"
    assert captured_calls[0]["workspace_resolution"].workspace_key == "coding"
    assert captured_calls[0]["commit"] is False
    assert captured_calls[0]["hydrate_precommit_bundle"] is False
    assert captured_calls[0]["bootstrap_empty_repo"] is True
