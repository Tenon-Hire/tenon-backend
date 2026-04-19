from __future__ import annotations

import pytest

from app.config import settings
from tests.trials.routes.trials_api_utils import *


@pytest.mark.asyncio
async def test_invite_preprovisions_day2_day3_workspaces(
    async_client,
    async_session,
    auth_header_factory,
    override_dependencies,
    monkeypatch,
):
    talent_partner = await create_talent_partner(async_session, email="preprov@app.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)

    day2_tasks = [t for t in tasks if t.day_index == 2]
    day3_tasks = [t for t in tasks if t.day_index == 3]
    assert day2_tasks and day3_tasks
    day2_tasks[0].type = "code"
    day3_tasks[0].type = "code"
    await async_session.commit()
    monkeypatch.setattr(settings.github, "GITHUB_ORG", "winoe-ai-repos")

    class StubGithubClient:
        def __init__(self):
            self.created_repos: list[tuple[str, str]] = []
            self.tree_entries: list[dict] = []
            self.created_refs: list[tuple[str, str]] = []

        async def generate_repo_from_template(self, **_kwargs):
            raise AssertionError("generate_repo_from_template should not be called")

        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            self.created_repos.append((owner, repo_name))
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 100 + len(self.created_repos),
                "default_branch": default_branch,
            }

        async def get_file_contents(self, repo_full_name, file_path, *, ref=None):
            raise GithubError("missing", status_code=404)

        async def get_branch(self, repo_full_name, branch):
            raise GithubError("missing", status_code=404)

        async def create_tree(self, repo_full_name, *, tree, base_tree=None):
            self.tree_entries = tree
            return {"sha": "tree-sha"}

        async def create_commit(self, repo_full_name, *, message, tree, parents):
            return {"sha": "commit-sha"}

        async def create_ref(self, repo_full_name, *, ref, sha):
            self.created_refs.append((ref, sha))
            return {"ref": ref, "sha": sha}

        async def create_codespace(
            self,
            repo_full_name,
            *,
            ref=None,
            devcontainer_path=None,
            machine=None,
            location=None,
        ):
            return {
                "name": f"codespace-{repo_full_name.split('/', 1)[-1]}",
                "state": "available",
                "web_url": "https://codespace.example",
            }

        async def add_collaborator(
            self, repo_full_name, username, *, permission="push"
        ):
            return {"ok": True}

    provider = MemoryEmailProvider()
    email_service = EmailService(provider, sender="noreply@test.com")
    stub_client = StubGithubClient()

    with override_dependencies(
        {
            get_email_service: lambda: email_service,
            get_github_client: lambda: stub_client,
        }
    ):
        res = await async_client.post(
            f"/api/trials/{sim.id}/invite",
            json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
            headers=auth_header_factory(talent_partner),
        )

    assert res.status_code == 200, res.text
    first_body = res.json()
    assert first_body["outcome"] == "created"

    with override_dependencies(
        {
            get_email_service: lambda: email_service,
            get_github_client: lambda: stub_client,
        }
    ):
        resend_res = await async_client.post(
            f"/api/trials/{sim.id}/invite",
            json={"candidateName": "Jane Doe", "inviteEmail": "jane@example.com"},
            headers=auth_header_factory(talent_partner),
        )

    assert resend_res.status_code == 200, resend_res.text
    assert resend_res.json()["outcome"] == "resent"

    cs = (await async_session.execute(select(CandidateSession))).scalar_one()
    workspaces = (
        (
            await async_session.execute(
                select(Workspace).where(Workspace.candidate_session_id == cs.id)
            )
        )
        .scalars()
        .all()
    )
    workspace_groups = (
        (
            await async_session.execute(
                select(WorkspaceGroup).where(
                    WorkspaceGroup.candidate_session_id == cs.id
                )
            )
        )
        .scalars()
        .all()
    )

    assert len(stub_client.created_repos) == 1
    expected_repo_name = f"winoe-ws-{cs.id}"
    assert stub_client.created_repos[0] == ("winoe-ai-repos", expected_repo_name)
    assert [entry["path"] for entry in stub_client.tree_entries] == [
        ".devcontainer/devcontainer.json",
        ".gitignore",
        ".github/workflows/evidence-capture.yml",
        "README.md",
    ]
    readme_entry = next(
        entry for entry in stub_client.tree_entries if entry["path"] == "README.md"
    )
    assert "Project Brief" in readme_entry["content"]
    assert "Business Context" in readme_entry["content"]
    assert "Acceptance Criteria" not in readme_entry["content"]
    assert stub_client.created_refs == [("refs/heads/main", "commit-sha")]
    assert len(workspace_groups) == 1
    assert workspace_groups[0].workspace_key == "coding"
    assert len(workspaces) == 1
    assert workspaces[0].workspace_group_id == workspace_groups[0].id
    assert workspaces[0].repo_full_name == f"winoe-ai-repos/{expected_repo_name}"
    assert workspace_groups[0].repo_full_name == f"winoe-ai-repos/{expected_repo_name}"
    assert all(ws.base_template_sha == "commit-sha" for ws in workspaces)
