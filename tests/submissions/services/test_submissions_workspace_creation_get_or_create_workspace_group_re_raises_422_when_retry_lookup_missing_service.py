from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_workspace_creation_service_utils import *


@pytest.mark.asyncio
async def test_get_or_create_workspace_group_re_raises_422_when_retry_lookup_missing(
    monkeypatch,
):
    async def _get_workspace_group(*_args, **_kwargs):
        return None

    async def _generate_template_repo(**_kwargs):
        raise GithubError("already exists", status_code=422)

    monkeypatch.setattr(wc.workspace_repo, "get_workspace_group", _get_workspace_group)
    monkeypatch.setattr(wc, "generate_template_repo", _generate_template_repo)

    with pytest.raises(GithubError) as excinfo:
        await wc._get_or_create_workspace_group(
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
    assert excinfo.value.status_code == 422
