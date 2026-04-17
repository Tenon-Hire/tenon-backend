from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.integrations.github.client import GithubError
from app.submissions.services import (
    submissions_services_submissions_workspace_bootstrap_service as bootstrap_service,
)


@pytest.mark.asyncio
async def test_bootstrap_empty_candidate_repo_writes_only_allowed_files():
    candidate_session = SimpleNamespace(id=77)
    trial = SimpleNamespace(
        title="Enable candidate invite flow",
        role="Backend Engineer",
    )
    scenario_version = SimpleNamespace(
        storyline_md="# From scratch candidate repo",
        project_brief_md=(
            "# Project Brief\n\n## Business Context\n\nBuild a candidate repo from scratch.\n"
            "\n## System Requirements\n\nCreate the invite repo baseline and preserve the brief.\n"
            "\n## Deliverables\n\n- The repo contains only the approved bootstrap files.\n"
            "- The repo is ready for a two-day from-scratch build.\n"
        ),
    )

    class StubGithubClient:
        def __init__(self):
            self.created_repo = None
            self.tree_entries = None
            self.ref = None
            self.codespace_request = None

        async def generate_repo_from_template(self, **_kwargs):
            raise AssertionError("generate_repo_from_template should not be called")

        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            self.created_repo = (owner, repo_name, private, default_branch)
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 123,
                "default_branch": default_branch,
            }

        async def get_file_contents(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def get_branch(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def create_tree(self, _repo_full_name, *, tree, base_tree=None):
            self.tree_entries = tree
            return {"sha": "tree-sha"}

        async def create_commit(self, _repo_full_name, *, message, tree, parents):
            return {"sha": "commit-sha"}

        async def create_ref(self, _repo_full_name, *, ref, sha):
            self.ref = (ref, sha)
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
            self.codespace_request = {
                "repo_full_name": repo_full_name,
                "ref": ref,
                "devcontainer_path": devcontainer_path,
                "machine": machine,
                "location": location,
            }
            return {
                "name": "codespace-77",
                "state": "available",
                "web_url": "https://codespace-77.github.dev",
            }

    client = StubGithubClient()
    result = await bootstrap_service.bootstrap_empty_candidate_repo(
        github_client=client,
        candidate_session=candidate_session,
        trial=trial,
        scenario_version=scenario_version,
        task=SimpleNamespace(title="Day 2 coding"),
        repo_prefix="winoe-ws-",
        destination_owner="winoe-ai-repos",
    )

    assert result.repo_full_name == "winoe-ai-repos/winoe-ws-77"
    assert result.template_repo_full_name is None
    assert result.codespace_name == "codespace-77"
    assert result.codespace_state == "available"
    assert result.codespace_url == "https://codespace-77.github.dev"
    assert [entry["path"] for entry in client.tree_entries] == [
        ".devcontainer/devcontainer.json",
        ".gitignore",
        ".github/workflows/evidence-capture.yml",
        "README.md",
    ]
    readme_entry = next(
        entry for entry in client.tree_entries if entry["path"] == "README.md"
    )
    assert "Build a candidate repo from scratch." in readme_entry["content"]
    assert (
        "The repo is ready for a two-day from-scratch build." in readme_entry["content"]
    )
    assert client.ref == ("refs/heads/main", "commit-sha")
    assert client.codespace_request == {
        "repo_full_name": "winoe-ai-repos/winoe-ws-77",
        "ref": "main",
        "devcontainer_path": ".devcontainer/devcontainer.json",
        "machine": None,
        "location": None,
    }


@pytest.mark.asyncio
async def test_bootstrap_empty_candidate_repo_uses_canonical_project_brief_helper(
    monkeypatch,
):
    candidate_session = SimpleNamespace(id=78)
    trial = SimpleNamespace(title="Helper trial", role="Backend Engineer")
    scenario_version = SimpleNamespace(
        storyline_md="# Helper scenario",
        project_brief_md="# Project Brief\n\n## Business Context\n\nHelper brief.\n",
        codespace_spec_json=None,
    )

    captured = {}

    def _canonical_project_brief_markdown(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return scenario_version.project_brief_md

    monkeypatch.setattr(
        bootstrap_service,
        "canonical_project_brief_markdown",
        _canonical_project_brief_markdown,
    )

    class StubGithubClient:
        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 321,
                "default_branch": default_branch,
            }

        async def get_file_contents(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def get_branch(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def create_tree(self, _repo_full_name, *, tree, base_tree=None):
            return {"sha": "tree-sha"}

        async def create_commit(self, _repo_full_name, *, message, tree, parents):
            return {"sha": "commit-sha"}

        async def create_ref(self, _repo_full_name, *, ref, sha):
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
                "name": "codespace-78",
                "state": "available",
                "web_url": "https://codespace-78.github.dev",
            }

    await bootstrap_service.bootstrap_empty_candidate_repo(
        github_client=StubGithubClient(),
        candidate_session=candidate_session,
        trial=trial,
        scenario_version=scenario_version,
        task=None,
        repo_prefix="winoe-ws-",
        destination_owner="winoe-ai-repos",
    )

    assert captured["args"][0] is scenario_version
    assert captured["kwargs"]["trial_title"] == trial.title
    assert captured["kwargs"]["storyline_md"] == scenario_version.storyline_md


@pytest.mark.asyncio
async def test_bootstrap_empty_candidate_repo_initializes_empty_repo_via_contents_api():
    candidate_session = SimpleNamespace(id=88)
    trial = SimpleNamespace(
        title="Enable candidate invite flow",
        role="Backend Engineer",
    )
    scenario_version = SimpleNamespace(
        storyline_md="# Empty repo bootstrap",
        project_brief_md=(
            "# Project Brief\n\n## Business Context\n\nBootstrap an empty candidate repo.\n"
            "\n## System Requirements\n\nInitialize the repo without pre-populated code.\n"
            "\n## Deliverables\n\n- The repo contains the from-scratch bootstrap files only.\n"
        ),
    )

    class StubGithubClient:
        def __init__(self):
            self.seeded = False
            self.seed_calls = []
            self.created_blobs = []
            self.tree_entries = None
            self.commit_args = None
            self.ref_args = None
            self.codespace_request = None

        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 456,
                "default_branch": default_branch,
            }

        async def get_branch(self, *_args, **_kwargs):
            if not self.seeded:
                raise GithubError("missing", status_code=404)
            return {"commit": {"sha": "seed-sha"}}

        async def get_file_contents(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def create_or_update_file(self, repo_full_name, file_path, **kwargs):
            self.seeded = True
            self.seed_calls.append((repo_full_name, file_path, kwargs))
            return {"content": {"sha": "readme-sha"}}

        async def create_blob(self, _repo_full_name, *, content):
            sha = f"blob-{len(self.created_blobs) + 1}"
            self.created_blobs.append(content)
            return {"sha": sha}

        async def get_commit(self, _repo_full_name, sha):
            assert sha == "seed-sha"
            return {"tree": {"sha": "seed-tree-sha"}}

        async def create_tree(self, _repo_full_name, *, tree, base_tree=None):
            self.tree_entries = tree
            assert base_tree == "seed-tree-sha"
            assert all("sha" in entry for entry in tree)
            return {"sha": "tree-sha"}

        async def create_commit(self, _repo_full_name, *, message, tree, parents):
            self.commit_args = {
                "message": message,
                "tree": tree,
                "parents": parents,
            }
            return {"sha": "commit-sha"}

        async def update_ref(self, _repo_full_name, *, ref, sha, force=False):
            self.ref_args = (ref, sha, force)
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
            self.codespace_request = {
                "repo_full_name": repo_full_name,
                "ref": ref,
                "devcontainer_path": devcontainer_path,
                "machine": machine,
                "location": location,
            }
            return {
                "name": "codespace-88",
                "state": "available",
                "web_url": "https://codespace-88.github.dev",
            }

    client = StubGithubClient()
    result = await bootstrap_service.bootstrap_empty_candidate_repo(
        github_client=client,
        candidate_session=candidate_session,
        trial=trial,
        scenario_version=scenario_version,
        task=SimpleNamespace(title="Day 2 coding"),
        repo_prefix="winoe-ws-",
        destination_owner="winoe-ai-repos",
    )

    assert client.seed_calls[0][0] == "winoe-ai-repos/winoe-ws-88"
    assert client.seed_calls[0][1] == "README.md"
    assert client.seed_calls[0][2]["message"] == "chore: initialize candidate repo"
    assert client.seed_calls[0][2]["branch"] == "main"
    assert "Bootstrap an empty candidate repo." in client.seed_calls[0][2]["content"]
    assert len(client.created_blobs) == 4
    assert [entry["path"] for entry in client.tree_entries] == [
        ".devcontainer/devcontainer.json",
        ".gitignore",
        ".github/workflows/evidence-capture.yml",
        "README.md",
    ]
    assert client.commit_args == {
        "message": "chore: bootstrap candidate repo",
        "tree": "tree-sha",
        "parents": ["seed-sha"],
    }
    assert client.ref_args == ("heads/main", "commit-sha", True)
    assert result.bootstrap_commit_sha == "commit-sha"
    assert result.codespace_url == "https://codespace-88.github.dev"


@pytest.mark.asyncio
async def test_bootstrap_empty_candidate_repo_cleans_up_on_late_failure():
    candidate_session = SimpleNamespace(id=89)
    trial = SimpleNamespace(title="Cleanup trial", role="Backend Engineer")
    scenario_version = SimpleNamespace(
        storyline_md="# Cleanup",
        project_brief_md="# Project Brief\n\n## Business Context\n\nCleanup.\n",
    )

    class StubGithubClient:
        def __init__(self):
            self.deleted_repos = []
            self.seeded = False

        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 789,
                "default_branch": default_branch,
            }

        async def get_branch(self, *_args, **_kwargs):
            if not self.seeded:
                raise GithubError("missing", status_code=404)
            return {"commit": {"sha": "seed-sha"}}

        async def get_file_contents(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def create_or_update_file(self, *_args, **_kwargs):
            self.seeded = True
            return {"content": {"sha": "readme-sha"}}

        async def create_blob(self, _repo_full_name, *, content):
            return {"sha": "blob-sha"}

        async def get_commit(self, *_args, **_kwargs):
            return {"tree": {"sha": "seed-tree-sha"}}

        async def create_tree(self, *_args, **_kwargs):
            return {"sha": "tree-sha"}

        async def create_commit(self, *_args, **_kwargs):
            return {"sha": "commit-sha"}

        async def update_ref(self, *_args, **_kwargs):
            return {"ok": True}

        async def create_codespace(self, *_args, **_kwargs):
            raise GithubError("codespace failed", status_code=409)

        async def delete_repo(self, repo_full_name):
            self.deleted_repos.append(repo_full_name)
            return {}

    client = StubGithubClient()
    with pytest.raises(GithubError, match="codespace failed"):
        await bootstrap_service.bootstrap_empty_candidate_repo(
            github_client=client,
            candidate_session=candidate_session,
            trial=trial,
            scenario_version=scenario_version,
            task=SimpleNamespace(title="Day 2 coding"),
            repo_prefix="winoe-ws-",
            destination_owner="winoe-ai-repos",
        )

    assert client.deleted_repos == ["winoe-ai-repos/winoe-ws-89"]


@pytest.mark.asyncio
async def test_bootstrap_empty_candidate_repo_derives_legacy_project_brief():
    candidate_session = SimpleNamespace(id=90)
    trial = SimpleNamespace(title="Legacy brief trial", role="Backend Engineer")
    scenario_version = SimpleNamespace(
        storyline_md="# Legacy scenario",
        project_brief_md=None,
        codespace_spec_json={
            "summary": "Build a candidate-facing workflow.",
            "candidate_goal": "Deliver the core system from scratch.",
            "acceptance_criteria": ["The repo ships with a usable README."],
        },
    )

    class StubGithubClient:
        def __init__(self):
            self.tree_entries = None

        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 999,
                "default_branch": default_branch,
            }

        async def get_file_contents(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def get_branch(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def create_tree(self, _repo_full_name, *, tree, base_tree=None):
            self.tree_entries = tree
            return {"sha": "tree-sha"}

        async def create_commit(self, _repo_full_name, *, message, tree, parents):
            return {"sha": "commit-sha"}

        async def create_ref(self, _repo_full_name, *, ref, sha):
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
                "name": "codespace-90",
                "state": "available",
                "web_url": "https://codespace-90.github.dev",
            }

    client = StubGithubClient()
    result = await bootstrap_service.bootstrap_empty_candidate_repo(
        github_client=client,
        candidate_session=candidate_session,
        trial=trial,
        scenario_version=scenario_version,
        task=None,
        repo_prefix="winoe-ws-",
        destination_owner="winoe-ai-repos",
    )

    assert result.repo_full_name == "winoe-ai-repos/winoe-ws-90"
    readme_entry = next(
        entry for entry in client.tree_entries if entry["path"] == "README.md"
    )
    assert "Build a candidate-facing workflow." in readme_entry["content"]
    assert "Deliver the core system from scratch." in readme_entry["content"]
