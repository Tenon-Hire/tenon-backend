from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_workspace_creation_service_utils import *


@pytest.mark.asyncio
async def test_get_or_create_workspace_group_reuses_existing(monkeypatch):
    existing = SimpleNamespace(repo_full_name="org/coding")
    calls: list[tuple[str, str, str | None]] = []

    async def _get_workspace_group(*_args, **_kwargs):
        return existing

    async def _add_collaborator_if_needed(_client, repo, username):
        calls.append(("collab", repo, username))

    monkeypatch.setattr(wc.workspace_repo, "get_workspace_group", _get_workspace_group)
    monkeypatch.setattr(wc, "add_collaborator_if_needed", _add_collaborator_if_needed)

    group, repo_id = await wc._get_or_create_workspace_group(
        object(),
        candidate_session=SimpleNamespace(id=1),
        task=SimpleNamespace(id=2),
        workspace_key="coding",
        github_client=object(),
        github_username="octocat",
        repo_prefix="pref-",
        destination_owner="org",
        now=datetime.now(UTC),
    )

    assert group is existing
    assert repo_id is None
    assert calls == [("collab", "org/coding", "octocat")]
