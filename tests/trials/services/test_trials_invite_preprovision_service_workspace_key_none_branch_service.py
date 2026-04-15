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
        task,
        github_client,
        github_username,
        repo_prefix,
        destination_owner,
        now,
        workspace_resolution=None,
        commit=True,
        hydrate_precommit_bundle=True,
    ):
        captured_calls.append(
            {
                "candidate_session_id": candidate_session.id,
                "task_id": task.id,
                "destination_owner": destination_owner,
                "workspace_resolution": workspace_resolution,
                "commit": commit,
                "hydrate_precommit_bundle": hydrate_precommit_bundle,
            }
        )

    monkeypatch.setattr(
        preprovision_service.settings.github,
        "GITHUB_REPO_PREFIX",
        "winoe",
    )
    monkeypatch.setattr(
        preprovision_service.settings.github,
        "GITHUB_TEMPLATE_OWNER",
        "templates",
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

    candidate_session = SimpleNamespace(id=42, trial_id=7)
    tasks = [
        SimpleNamespace(id=501, day_index=2, type="code", template_repo="org/template")
    ]

    await preprovision_service.preprovision_workspaces(
        db=object(),
        candidate_session=candidate_session,
        tasks=tasks,
        github_client=object(),
        now=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
        fresh_candidate_session=True,
    )

    assert len(captured_calls) == 1
    assert captured_calls[0]["task_id"] == 501
    assert captured_calls[0]["destination_owner"] == "fallback-org"
    assert captured_calls[0]["workspace_resolution"] is None
    assert captured_calls[0]["commit"] is False
    assert captured_calls[0]["hydrate_precommit_bundle"] is False


@pytest.mark.asyncio
async def test_preprovision_workspaces_reraises_github_error_for_workspace_key(
    monkeypatch,
):
    captured_calls: list[dict] = []

    async def _ensure_workspace(
        _db,
        *,
        candidate_session,
        task,
        github_client,
        github_username,
        repo_prefix,
        destination_owner,
        now,
        workspace_resolution=None,
        commit=True,
        hydrate_precommit_bundle=True,
    ):
        captured_calls.append(
            {
                "candidate_session_id": candidate_session.id,
                "task_id": task.id,
                "destination_owner": destination_owner,
                "workspace_resolution": workspace_resolution,
                "commit": commit,
                "hydrate_precommit_bundle": hydrate_precommit_bundle,
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

    candidate_session = SimpleNamespace(id=42, trial_id=7)
    task = SimpleNamespace(
        id=501,
        day_index=2,
        type="code",
        template_repo="org/template",
    )

    with pytest.raises(preprovision_service.GithubError):
        await preprovision_service.preprovision_workspaces(
            db=object(),
            candidate_session=candidate_session,
            tasks=[task],
            github_client=object(),
            now=datetime(2026, 3, 27, 12, 0, tzinfo=UTC),
            fresh_candidate_session=True,
        )

    assert len(captured_calls) == 1
    assert captured_calls[0]["destination_owner"] == "winoe-ai-repos"
    assert captured_calls[0]["workspace_resolution"].workspace_key == "coding"
    assert captured_calls[0]["commit"] is False
    assert captured_calls[0]["hydrate_precommit_bundle"] is False
