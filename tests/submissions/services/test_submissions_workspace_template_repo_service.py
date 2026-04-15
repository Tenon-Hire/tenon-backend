from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.submissions.services import (
    submissions_services_submissions_workspace_template_repo_service as template_repo_service,
)


@pytest.mark.asyncio
async def test_generate_template_repo_canonicalizes_stale_template_repo():
    observed: dict[str, object] = {}

    class StubGithubClient:
        async def generate_repo_from_template(self, **kwargs):
            observed.update(kwargs)
            return {
                "owner": {"login": "winoe-ai-repos"},
                "name": "winoe-ws-11-coding",
                "default_branch": "main",
                "id": 7,
            }

    await template_repo_service.generate_template_repo(
        github_client=StubGithubClient(),
        candidate_session=SimpleNamespace(id=11),
        task=SimpleNamespace(
            id=22,
            template_repo="winoe-hire-dev/winoe-template-python-fastapi",
        ),
        repo_prefix="winoe-ws-",
        destination_owner="winoe-ai-repos",
        workspace_key="coding",
    )

    assert (
        observed["template_full_name"]
        == "winoe-ai-repos/winoe-ai-template-python-fastapi"
    )


@pytest.mark.asyncio
async def test_generate_template_repo_requires_destination_owner():
    class StubGithubClient:
        async def generate_repo_from_template(self, **_kwargs):
            raise AssertionError("generate_repo_from_template should not be called")

    with pytest.raises(HTTPException) as exc_info:
        await template_repo_service.generate_template_repo(
            github_client=StubGithubClient(),
            candidate_session=SimpleNamespace(id=11),
            task=SimpleNamespace(id=22, template_repo="org/template"),
            repo_prefix="winoe-ws-",
            destination_owner=None,
            workspace_key="coding",
        )

    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_generate_template_repo_normalizes_returned_identity():
    class StubGithubClient:
        async def generate_repo_from_template(self, **_kwargs):
            return {
                "owner": {"login": "winoe-ai-repos"},
                "name": "winoe-ws-11-coding",
                "default_branch": "main",
                "id": 7,
            }

    (
        template_repo,
        repo_full_name,
        default_branch,
        repo_id,
    ) = await template_repo_service.generate_template_repo(
        github_client=StubGithubClient(),
        candidate_session=SimpleNamespace(id=11),
        task=SimpleNamespace(id=22, template_repo="org/template"),
        repo_prefix="winoe-ws-",
        destination_owner="winoe-ai-repos",
        workspace_key="coding",
    )

    assert template_repo == "org/template"
    assert repo_full_name == "winoe-ai-repos/winoe-ws-11-coding"
    assert default_branch == "main"
    assert repo_id == 7


@pytest.mark.asyncio
async def test_generate_template_repo_rejects_owner_mismatch():
    class StubGithubClient:
        async def generate_repo_from_template(self, **_kwargs):
            return {
                "owner": {"login": "wrong-org"},
                "name": "winoe-ws-11-coding",
                "full_name": "wrong-org/winoe-ws-11-coding",
                "default_branch": "main",
                "id": 7,
            }

    with pytest.raises(HTTPException) as exc_info:
        await template_repo_service.generate_template_repo(
            github_client=StubGithubClient(),
            candidate_session=SimpleNamespace(id=11),
            task=SimpleNamespace(id=22, template_repo="org/template"),
            repo_prefix="winoe-ws-",
            destination_owner="winoe-ai-repos",
            workspace_key="coding",
        )

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_generate_template_repo_rejects_repo_name_mismatch():
    class StubGithubClient:
        async def generate_repo_from_template(self, **_kwargs):
            return {
                "owner": {"login": "winoe-ai-repos"},
                "name": "wrong-repo",
                "full_name": "winoe-ai-repos/wrong-repo",
                "default_branch": "main",
                "id": 7,
            }

    with pytest.raises(HTTPException) as exc_info:
        await template_repo_service.generate_template_repo(
            github_client=StubGithubClient(),
            candidate_session=SimpleNamespace(id=11),
            task=SimpleNamespace(id=22, template_repo="org/template"),
            repo_prefix="winoe-ws-",
            destination_owner="winoe-ai-repos",
            workspace_key="coding",
        )

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_generate_template_repo_rejects_full_name_owner_mismatch():
    class StubGithubClient:
        async def generate_repo_from_template(self, **_kwargs):
            return {
                "owner": {"login": "wrong-org"},
                "name": "winoe-ws-11-coding",
                "full_name": "winoe-ai-repos/winoe-ws-11-coding",
                "default_branch": "main",
                "id": 7,
            }

    with pytest.raises(HTTPException) as exc_info:
        await template_repo_service.generate_template_repo(
            github_client=StubGithubClient(),
            candidate_session=SimpleNamespace(id=11),
            task=SimpleNamespace(id=22, template_repo="org/template"),
            repo_prefix="winoe-ws-",
            destination_owner="winoe-ai-repos",
            workspace_key="coding",
        )

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_generate_template_repo_rejects_malformed_full_name_identity():
    class StubGithubClient:
        async def generate_repo_from_template(self, **_kwargs):
            return {
                "owner": {"login": "winoe-ai-repos"},
                "name": "winoe-ws-11-coding",
                "full_name": "bad",
                "default_branch": "main",
                "id": 7,
            }

    with pytest.raises(HTTPException) as exc_info:
        await template_repo_service.generate_template_repo(
            github_client=StubGithubClient(),
            candidate_session=SimpleNamespace(id=11),
            task=SimpleNamespace(id=22, template_repo="org/template"),
            repo_prefix="winoe-ws-",
            destination_owner="winoe-ai-repos",
            workspace_key="coding",
        )

    assert exc_info.value.status_code == 502
