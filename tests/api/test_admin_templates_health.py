import pytest

from app.api.dependencies.github_native import get_github_client
from app.domains.github_native import GithubError
from app.domains.tasks.template_catalog import TEMPLATE_CATALOG
from app.infra.security.current_user import get_current_user


class FakeRecruiter:
    role = "recruiter"


class MissingWorkflowGithubClient:
    async def get_repo(self, repo_full_name: str):
        return {"default_branch": "main"}

    async def get_branch(self, repo_full_name: str, branch: str):
        return {"commit": {"sha": "abc123"}}

    async def get_file_contents(
        self, repo_full_name: str, file_path: str, *, ref: str | None = None
    ):
        raise GithubError("not found", status_code=404)


@pytest.mark.asyncio
async def test_admin_template_health_ok(async_client, override_dependencies):
    async def override_get_current_user():
        return FakeRecruiter()

    with override_dependencies({get_current_user: override_get_current_user}):
        resp = await async_client.get("/api/admin/templates/health")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert len(payload["templates"]) == len(TEMPLATE_CATALOG)
    assert all(item["ok"] is True for item in payload["templates"])


@pytest.mark.asyncio
async def test_admin_template_health_missing_workflow(
    async_client, override_dependencies
):
    async def override_get_current_user():
        return FakeRecruiter()

    with override_dependencies(
        {
            get_current_user: override_get_current_user,
            get_github_client: lambda: MissingWorkflowGithubClient(),
        }
    ):
        resp = await async_client.get("/api/admin/templates/health")

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is False
    assert payload["templates"]
    assert payload["templates"][0]["ok"] is False
    assert "workflow_file_missing" in payload["templates"][0]["errors"]
