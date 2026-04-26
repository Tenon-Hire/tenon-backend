from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.integrations.github import GithubError
from app.submissions.services.submissions_services_submissions_workspace_bootstrap_service import (
    bootstrap_empty_candidate_repo,
    build_evidence_capture_workflow_yaml,
)


class _BootstrapGithubClient:
    def __init__(self, *, codespace_error: GithubError | None = None) -> None:
        self.codespace_error = codespace_error
        self.created_empty_repos: list[dict[str, object]] = []
        self.generated_from_template = False
        self.tree_entries: list[dict[str, object]] = []

    async def generate_repo_from_template(self, **_kwargs):
        self.generated_from_template = True
        raise AssertionError("from-scratch bootstrap must not use templates")

    async def create_empty_repo(
        self, *, owner: str, repo_name: str, private: bool, default_branch: str
    ):
        self.created_empty_repos.append(
            {
                "owner": owner,
                "repo_name": repo_name,
                "private": private,
                "default_branch": default_branch,
            }
        )
        return {
            "id": 101,
            "full_name": f"{owner}/{repo_name}",
            "default_branch": default_branch,
        }

    async def get_repo(self, repo_full_name: str):
        return {"id": 101, "full_name": repo_full_name, "default_branch": "main"}

    async def get_branch(self, *_args, **_kwargs):
        raise GithubError("branch missing", status_code=404)

    async def get_file_contents(self, *_args, **_kwargs):
        raise GithubError("file missing", status_code=404)

    async def create_tree(self, _repo_full_name: str, *, tree, base_tree=None):
        self.tree_entries = list(tree)
        return {"sha": "tree-sha"}

    async def create_commit(self, *_args, **_kwargs):
        return {"sha": "bootstrap-sha"}

    async def create_ref(self, *_args, **_kwargs):
        return {"ref": "refs/heads/main"}

    async def create_codespace(self, *_args, **_kwargs):
        if self.codespace_error is not None:
            raise self.codespace_error
        return {
            "name": "repo-7-main",
            "state": "Available",
            "web_url": "https://codespaces.example/repo-7",
        }


def _scenario_version() -> SimpleNamespace:
    return SimpleNamespace(
        project_brief_md=(
            "# Project Brief\n\n"
            "## Business Context\n\n"
            "Build a scheduling workflow from an empty repository."
        ),
        storyline_md="Candidate builds the system from scratch.",
    )


@pytest.mark.asyncio
async def test_empty_repo_bootstrap_uses_empty_repo_and_only_seed_files() -> None:
    github_client = _BootstrapGithubClient()

    result = await bootstrap_empty_candidate_repo(
        github_client=github_client,
        candidate_session=SimpleNamespace(id=7),
        trial=SimpleNamespace(id=3, title="Scheduling Trial"),
        scenario_version=_scenario_version(),
        task=SimpleNamespace(id=2, title="Implementation"),
        repo_prefix="candidate-",
        destination_owner="winoe-workspaces",
    )

    assert github_client.created_empty_repos == [
        {
            "owner": "winoe-workspaces",
            "repo_name": "candidate-7",
            "private": True,
            "default_branch": "main",
        }
    ]
    assert github_client.generated_from_template is False
    assert result.repo_full_name == "winoe-workspaces/candidate-7"
    assert result.template_repo_full_name is None
    assert result.bootstrap_commit_sha == "bootstrap-sha"
    assert result.codespace_url == "https://codespaces.example/repo-7"

    seeded_files = {
        entry["path"]: entry["content"] for entry in github_client.tree_entries
    }
    assert set(seeded_files) == {
        ".devcontainer/devcontainer.json",
        "README.md",
        ".gitignore",
        ".github/workflows/winoe-evidence-capture.yml",
    }
    assert "# Project Brief" in str(seeded_files["README.md"])
    assert "Build a scheduling workflow" in str(seeded_files["README.md"])
    assert "package.json" not in seeded_files
    assert "pyproject.toml" not in seeded_files
    assert "src/" not in seeded_files


def test_evidence_capture_workflow_covers_core_review_artifacts() -> None:
    workflow = build_evidence_capture_workflow_yaml()

    for expected in (
        "file_creation_timeline.json",
        "test_detection.json",
        "test_results.json",
        "lint_detection.json",
        "lint_results.json",
        "evidence_manifest.json",
        "commit_metadata.json",
        "repo_tree_summary.json",
        "actions/upload-artifact@v4",
    ):
        assert expected in workflow


@pytest.mark.asyncio
async def test_codespace_service_unavailable_degrades_to_repo_only() -> None:
    github_client = _BootstrapGithubClient(
        codespace_error=GithubError("unavailable", status_code=503)
    )

    result = await bootstrap_empty_candidate_repo(
        github_client=github_client,
        candidate_session=SimpleNamespace(id=8),
        trial=SimpleNamespace(id=3, title="Scheduling Trial"),
        scenario_version=_scenario_version(),
        task=None,
        repo_prefix="candidate-",
        destination_owner="winoe-workspaces",
    )

    assert result.repo_full_name == "winoe-workspaces/candidate-8"
    assert result.codespace_name is None
    assert result.codespace_state is None
    assert (
        result.codespace_url
        == "https://codespaces.new/winoe-workspaces/candidate-8?quickstart=1"
    )


@pytest.mark.asyncio
async def test_hard_codespace_errors_do_not_degrade() -> None:
    github_client = _BootstrapGithubClient(
        codespace_error=GithubError("bad credentials", status_code=401)
    )

    with pytest.raises(GithubError, match="bad credentials"):
        await bootstrap_empty_candidate_repo(
            github_client=github_client,
            candidate_session=SimpleNamespace(id=9),
            trial=SimpleNamespace(id=3, title="Scheduling Trial"),
            scenario_version=_scenario_version(),
            task=None,
            repo_prefix="candidate-",
            destination_owner="winoe-workspaces",
        )
