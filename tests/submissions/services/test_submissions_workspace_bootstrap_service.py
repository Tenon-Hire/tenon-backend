from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
import yaml

from app.integrations.github.client import GithubError
from app.submissions.services import (
    submissions_services_submissions_workspace_bootstrap_service as bootstrap_service,
)


def test_build_evidence_capture_workflow_yaml_is_valid_and_structured():
    workflow_text = bootstrap_service.build_evidence_capture_workflow_yaml()

    parsed = yaml.load(workflow_text, Loader=yaml.BaseLoader)

    assert parsed["name"] == "Winoe Evidence Capture"
    assert parsed["on"]["push"] in ({}, None, "")
    assert "workflow_dispatch" in parsed["on"]

    steps = parsed["jobs"]["capture"]["steps"]
    checkout_step = next(
        step for step in steps if step["uses"] == "actions/checkout@v4"
    )
    assert checkout_step["with"]["fetch-depth"] == "0"

    capture_step = next(step for step in steps if step["name"] == "Capture evidence")
    assert capture_step["continue-on-error"] == "true"

    upload_steps = {
        step["with"]["name"]: step
        for step in steps
        if step.get("uses") == "actions/upload-artifact@v4"
    }
    assert upload_steps["winoe-commit-metadata"]["with"]["retention-days"] == "90"
    assert (
        upload_steps["winoe-file-creation-timeline"]["with"]["retention-days"] == "90"
    )
    assert upload_steps["winoe-repo-tree-summary"]["with"]["retention-days"] == "90"
    assert upload_steps["winoe-dependency-manifests"]["with"]["retention-days"] == "90"
    assert upload_steps["winoe-test-detection"]["with"]["retention-days"] == "90"
    assert upload_steps["winoe-test-results"]["with"]["retention-days"] == "90"
    assert upload_steps["winoe-lint-detection"]["with"]["retention-days"] == "90"
    assert upload_steps["winoe-lint-results"]["with"]["retention-days"] == "90"
    assert upload_steps["winoe-evidence-manifest"]["with"]["retention-days"] == "90"


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
            self.events: list[str] = []

        async def generate_repo_from_template(self, **_kwargs):
            raise AssertionError("generate_repo_from_template should not be called")

        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            self.events.append("create_empty_repo")
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
            self.events.append("create_codespace")
            return {
                "name": "codespace-77",
                "state": "available",
                "web_url": "https://codespace-77.github.dev",
            }

        async def get_authenticated_user_login(self):
            self.events.append("get_authenticated_user_login")
            return "RobelKDev"

        async def add_collaborator(
            self, repo_full_name, username, *, permission="push"
        ):
            self.events.append(f"add_collaborator:{username}:{permission}")
            return {"ok": True}

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
        "README.md",
        ".gitignore",
        ".github/workflows/winoe-evidence-capture.yml",
    ]
    assert ".github/workflows/evidence-capture.yml" not in {
        entry["path"] for entry in client.tree_entries
    }
    workflow_entry = next(
        entry
        for entry in client.tree_entries
        if entry["path"] == ".github/workflows/winoe-evidence-capture.yml"
    )
    workflow_text = workflow_entry["content"]
    assert "push:" in workflow_text
    assert "continue-on-error: true" in workflow_text
    assert "fetch-depth: 0" in workflow_text
    assert "retention-days: 90" in workflow_text
    assert "commit_metadata.json" in workflow_text
    assert "file_creation_timeline.json" in workflow_text
    assert "repo_tree_summary.json" in workflow_text
    assert "dependency_manifests.json" in workflow_text
    assert "test_detection.json" in workflow_text
    assert "test_results.json" in workflow_text
    assert "lint_detection.json" in workflow_text
    assert "lint_results.json" in workflow_text
    assert "evidence_manifest.json" in workflow_text
    assert "package.json found without test or lint scripts" in workflow_text
    assert "detected package.json scripts" in workflow_text
    assert "detected Python project manifest and common test paths" in workflow_text
    assert (
        "detected Python project manifest without obvious test paths" in workflow_text
    )
    assert "no supported manifest with a runnable command found" in workflow_text
    gitignore_entry = next(
        entry for entry in client.tree_entries if entry["path"] == ".gitignore"
    )
    assert "package-lock.json" not in gitignore_entry["content"]
    assert "pnpm-lock.yaml" not in gitignore_entry["content"]
    assert "yarn.lock" not in gitignore_entry["content"]
    assert gitignore_entry["content"].count(".vscode/") == 1
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
    assert client.events == [
        "create_empty_repo",
        "get_authenticated_user_login",
        "add_collaborator:RobelKDev:push",
        "create_codespace",
    ]


@pytest.mark.asyncio
async def test_bootstrap_empty_candidate_repo_degrades_only_when_codespace_service_is_unavailable(
    caplog,
):
    candidate_session = SimpleNamespace(id=79)
    trial = SimpleNamespace(
        title="Codespace outage trial",
        role="Backend Engineer",
    )
    scenario_version = SimpleNamespace(
        storyline_md="# Codespace outage scenario",
        project_brief_md="# Project Brief\n\n## Business Context\n\nOutage probe.\n",
    )

    class StubGithubClient:
        def __init__(self):
            self.events: list[str] = []

        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            self.events.append("create_empty_repo")
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 456,
                "default_branch": default_branch,
            }

        async def get_file_contents(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def get_branch(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def create_blob(self, *_args, **_kwargs):
            self.events.append("create_blob")
            return {"sha": "blob-sha"}

        async def create_tree(self, _repo_full_name, *, tree, base_tree=None):
            self.events.append("create_tree")
            return {"sha": "tree-sha"}

        async def create_commit(self, _repo_full_name, *, message, tree, parents):
            self.events.append("create_commit")
            return {"sha": "commit-sha"}

        async def create_ref(self, _repo_full_name, *, ref, sha):
            self.events.append("create_ref")
            return {"ref": ref, "sha": sha}

        async def get_authenticated_user_login(self):
            self.events.append("get_authenticated_user_login")
            return "RobelKDev"

        async def add_collaborator(
            self, repo_full_name, username, *, permission="push"
        ):
            self.events.append(f"add_collaborator:{username}:{permission}")
            return {"ok": True}

        async def create_codespace(
            self,
            repo_full_name,
            *,
            ref=None,
            devcontainer_path=None,
            machine=None,
            location=None,
        ):
            self.events.append("create_codespace")
            raise GithubError(
                "GitHub Codespaces service unavailable",
                status_code=503,
            )

    client = StubGithubClient()
    with caplog.at_level(logging.WARNING):
        result = await bootstrap_service.bootstrap_empty_candidate_repo(
            github_client=client,
            candidate_session=candidate_session,
            trial=trial,
            scenario_version=scenario_version,
            task=SimpleNamespace(title="Day 2 coding"),
            repo_prefix="winoe-ws-",
            destination_owner="winoe-ai-repos",
        )

    assert result.repo_full_name == "winoe-ai-repos/winoe-ws-79"
    assert result.codespace_name is None
    assert result.codespace_state is None
    assert (
        result.codespace_url
        == "https://codespaces.new/winoe-ai-repos/winoe-ws-79?quickstart=1"
    )
    assert any(
        record.message == "github_codespace_provision_degraded"
        and record.__dict__.get("fallback_reason")
        == "github_codespace_service_unavailable"
        and record.__dict__.get("status_code") == 503
        and record.__dict__.get("fallback_mode") == "repo_only"
        and record.__dict__.get("safe_fallback") is True
        for record in caplog.records
    )
    assert client.events == [
        "create_empty_repo",
        "create_blob",
        "create_blob",
        "create_blob",
        "create_blob",
        "create_tree",
        "create_commit",
        "create_ref",
        "get_authenticated_user_login",
        "add_collaborator:RobelKDev:push",
        "create_codespace",
    ]


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
async def test_bootstrap_empty_candidate_repo_retries_codespace_not_found_then_falls_back_to_repo_only(
    caplog, monkeypatch
):
    candidate_session = SimpleNamespace(id=79)
    trial = SimpleNamespace(title="Codespace fallback trial", role="Backend Engineer")
    scenario_version = SimpleNamespace(
        storyline_md="# Codespace fallback",
        project_brief_md=(
            "# Project Brief\n\n## Business Context\n\nFallback candidate repo.\n"
        ),
    )

    class StubGithubClient:
        def __init__(self):
            self.codespace_attempts = 0

        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 444,
                "default_branch": default_branch,
            }

        async def get_file_contents(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def get_branch(self, *_args, **_kwargs):
            raise GithubError("missing", status_code=404)

        async def create_or_update_file(self, *_args, **_kwargs):
            return {"content": {"sha": "readme-sha"}}

        async def create_tree(self, _repo_full_name, *, tree, base_tree=None):
            return {"sha": "tree-sha"}

        async def create_commit(self, _repo_full_name, *, message, tree, parents):
            return {"sha": "commit-sha"}

        async def update_ref(self, _repo_full_name, *, ref, sha, force=False):
            return {"ref": ref, "sha": sha, "force": force}

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
            self.codespace_attempts += 1
            raise GithubError("missing", status_code=404)

    sleep_calls: list[int] = []

    async def _sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(bootstrap_service.asyncio, "sleep", _sleep)

    with caplog.at_level(logging.WARNING):
        result = await bootstrap_service.bootstrap_empty_candidate_repo(
            github_client=StubGithubClient(),
            candidate_session=candidate_session,
            trial=trial,
            scenario_version=scenario_version,
            task=None,
            repo_prefix="winoe-ws-",
            destination_owner="winoe-ai-repos",
        )
    assert sleep_calls == [bootstrap_service._CODESPACE_RETRY_DELAY_SECONDS] * 6
    assert result.codespace_name is None
    assert result.codespace_state is None
    assert (
        result.codespace_url
        == "https://codespaces.new/winoe-ai-repos/winoe-ws-79?quickstart=1"
    )
    assert any(
        record.message == "github_codespace_provision_retrying"
        and record.__dict__.get("status_code") == 404
        and record.__dict__.get("retry_reason") == "repo_not_ready_yet"
        and record.__dict__.get("retryable") is True
        for record in caplog.records
    )
    assert any(
        record.message == "github_codespace_provision_degraded"
        and record.__dict__.get("fallback_reason")
        == "github_codespace_service_unavailable"
        and record.__dict__.get("status_code") == 404
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_bootstrap_empty_candidate_repo_retries_codespace_creation_with_short_delay(
    monkeypatch,
    caplog,
):
    candidate_session = SimpleNamespace(id=80)
    trial = SimpleNamespace(title="Retry trial", role="Backend Engineer")
    scenario_version = SimpleNamespace(
        storyline_md="# Retry",
        project_brief_md=(
            "# Project Brief\n\n## Business Context\n\nRetry candidate repo.\n"
        ),
    )
    sleep_calls: list[int] = []

    class StubGithubClient:
        def __init__(self):
            self.codespace_attempts = 0

        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 445,
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

        async def get_authenticated_user_login(self):
            return "octocat"

        async def add_collaborator(
            self, repo_full_name, username, *, permission="push"
        ):
            return {"ok": True}

        async def create_codespace(
            self,
            repo_full_name,
            *,
            ref=None,
            devcontainer_path=None,
            machine=None,
            location=None,
        ):
            self.codespace_attempts += 1
            if self.codespace_attempts < 3:
                raise GithubError("not ready", status_code=404)
            return {
                "name": "codespace-80",
                "state": "available",
                "web_url": "https://codespace-80.github.dev",
            }

    async def _sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(bootstrap_service.asyncio, "sleep", _sleep)

    with caplog.at_level(logging.WARNING):
        result = await bootstrap_service.bootstrap_empty_candidate_repo(
            github_client=StubGithubClient(),
            candidate_session=candidate_session,
            trial=trial,
            scenario_version=scenario_version,
            task=None,
            repo_prefix="winoe-ws-",
            destination_owner="winoe-ai-repos",
        )

    assert result.codespace_name == "codespace-80"
    assert result.codespace_state == "available"
    assert result.codespace_url == "https://codespace-80.github.dev"
    assert sleep_calls == [bootstrap_service._CODESPACE_RETRY_DELAY_SECONDS] * 2
    assert any(
        record.message == "github_codespace_provision_retrying"
        and record.__dict__.get("status_code") == 404
        and record.__dict__.get("retry_reason") == "repo_not_ready_yet"
        and record.__dict__.get("retryable") is True
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_bootstrap_empty_candidate_repo_does_not_degrade_on_generic_400(
    caplog,
):
    candidate_session = SimpleNamespace(id=92)
    trial = SimpleNamespace(title="Hard fail trial", role="Backend Engineer")
    scenario_version = SimpleNamespace(
        storyline_md="# Hard fail",
        project_brief_md="# Project Brief\n\n## Business Context\n\nHard fail.\n",
    )

    class StubGithubClient:
        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 446,
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
            raise GithubError(
                "GitHub API error (400) (https://api.github.com/repos/winoe-ai-repos/winoe-ws-92/codespaces)",
                status_code=400,
            )

    with caplog.at_level(logging.ERROR), pytest.raises(
        GithubError, match="GitHub API error"
    ):
        await bootstrap_service.bootstrap_empty_candidate_repo(
            github_client=StubGithubClient(),
            candidate_session=candidate_session,
            trial=trial,
            scenario_version=scenario_version,
            task=None,
            repo_prefix="winoe-ws-",
            destination_owner="winoe-ai-repos",
        )
    assert any(
        record.message == "github_codespace_provision_failed"
        and record.__dict__.get("status_code") == 400
        and record.__dict__.get("failure_class") == "hard_failure"
        and record.__dict__.get("retryable") is False
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_bootstrap_empty_candidate_repo_does_not_degrade_on_generic_500(
    caplog,
):
    candidate_session = SimpleNamespace(id=93)
    trial = SimpleNamespace(title="Unexpected error trial", role="Backend Engineer")
    scenario_version = SimpleNamespace(
        storyline_md="# Unexpected error",
        project_brief_md=(
            "# Project Brief\n\n## Business Context\n\nUnexpected failure.\n"
        ),
    )

    class StubGithubClient:
        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 447,
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
            raise GithubError("server exploded", status_code=500)

    with caplog.at_level(logging.ERROR), pytest.raises(
        GithubError, match="server exploded"
    ):
        await bootstrap_service.bootstrap_empty_candidate_repo(
            github_client=StubGithubClient(),
            candidate_session=candidate_session,
            trial=trial,
            scenario_version=scenario_version,
            task=None,
            repo_prefix="winoe-ws-",
            destination_owner="winoe-ai-repos",
        )
    assert any(
        record.message == "github_codespace_provision_failed"
        and record.__dict__.get("status_code") == 500
        and record.__dict__.get("failure_class") == "hard_failure"
        and record.__dict__.get("retryable") is False
        for record in caplog.records
    )


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
        "README.md",
        ".gitignore",
        ".github/workflows/winoe-evidence-capture.yml",
    ]
    workflow_text = client.created_blobs[3]
    assert "workflow_dispatch:" in workflow_text
    assert "continue-on-error: true" in workflow_text
    assert "retention-days: 90" in workflow_text
    assert "repo_tree_summary.json" in workflow_text
    assert "evidence_manifest.json" in workflow_text
    assert "package-lock.json" not in client.created_blobs[2]
    assert "pnpm-lock.yaml" not in client.created_blobs[2]
    assert "yarn.lock" not in client.created_blobs[2]
    assert client.commit_args == {
        "message": "chore: bootstrap candidate repo",
        "tree": "tree-sha",
        "parents": ["seed-sha"],
    }
    assert client.ref_args == ("heads/main", "commit-sha", True)
    assert result.bootstrap_commit_sha == "commit-sha"
    assert result.codespace_url == "https://codespace-88.github.dev"


@pytest.mark.asyncio
async def test_bootstrap_empty_candidate_repo_recovers_when_bootstrap_files_are_missing():
    candidate_session = SimpleNamespace(id=90)
    trial = SimpleNamespace(title="Recovery trial", role="Backend Engineer")
    scenario_version = SimpleNamespace(
        storyline_md="# Recovery",
        project_brief_md="# Project Brief\n\n## Business Context\n\nRecover partially seeded repos.\n",
    )

    collaborator_calls: list[tuple[str, str]] = []

    class StubGithubClient:
        def __init__(self):
            self.created_blobs = []
            self.tree_entries = None
            self.commit_args = None
            self.ref_args = None
            self.codespace_request = None
            self.created_repo_calls = 0

        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            self.created_repo_calls += 1
            raise GithubError("repo exists", status_code=422)

        async def get_repo(self, repo_full_name):
            return {
                "owner": {"login": repo_full_name.split("/", 1)[0]},
                "name": repo_full_name.split("/", 1)[1],
                "full_name": repo_full_name,
                "id": 999,
                "default_branch": "main",
            }

        async def get_branch(self, *_args, **_kwargs):
            return {"commit": {"sha": "existing-sha"}}

        async def get_file_contents(self, repo_full_name, file_path, *, ref=None):
            if file_path == "README.md":
                return {"content": "existing readme"}
            raise GithubError("missing", status_code=404)

        async def create_blob(self, _repo_full_name, *, content):
            sha = f"blob-{len(self.created_blobs) + 1}"
            self.created_blobs.append(content)
            return {"sha": sha}

        async def get_commit(self, _repo_full_name, sha):
            assert sha == "existing-sha"
            return {"tree": {"sha": "existing-tree-sha"}}

        async def create_tree(self, _repo_full_name, *, tree, base_tree=None):
            self.tree_entries = tree
            assert base_tree == "existing-tree-sha"
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

        async def get_authenticated_user_login(self):
            return "octocat"

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
                "name": "codespace-90",
                "state": "available",
                "web_url": "https://codespace-90.github.dev",
            }

    client = StubGithubClient()

    async def _add_collaborator_if_needed(github_client, repo_full_name, username):
        collaborator_calls.append((repo_full_name, username))

    original_add_collaborator = bootstrap_service.add_collaborator_if_needed
    bootstrap_service.add_collaborator_if_needed = _add_collaborator_if_needed
    try:
        result = await bootstrap_service.bootstrap_empty_candidate_repo(
            github_client=client,
            candidate_session=candidate_session,
            trial=trial,
            scenario_version=scenario_version,
            task=SimpleNamespace(title="Day 2 coding"),
            repo_prefix="winoe-ws-",
            destination_owner="winoe-ai-repos",
        )
    finally:
        bootstrap_service.add_collaborator_if_needed = original_add_collaborator

    assert client.created_repo_calls == 1
    assert len(client.created_blobs) == 4
    assert [entry["path"] for entry in client.tree_entries] == [
        ".devcontainer/devcontainer.json",
        "README.md",
        ".gitignore",
        ".github/workflows/winoe-evidence-capture.yml",
    ]
    assert collaborator_calls == [("winoe-ai-repos/winoe-ws-90", "octocat")]
    assert client.codespace_request == {
        "repo_full_name": "winoe-ai-repos/winoe-ws-90",
        "ref": "main",
        "devcontainer_path": ".devcontainer/devcontainer.json",
        "machine": None,
        "location": None,
    }
    assert result.bootstrap_commit_sha == "commit-sha"
    assert result.codespace_url == "https://codespace-90.github.dev"


@pytest.mark.asyncio
async def test_bootstrap_empty_candidate_repo_keeps_repo_on_late_failure():
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

    assert client.deleted_repos == []


@pytest.mark.asyncio
async def test_bootstrap_empty_candidate_repo_logs_phase_timings(caplog):
    candidate_session = SimpleNamespace(id=91)
    trial = SimpleNamespace(id=11, title="Timing trial", role="Backend Engineer")
    scenario_version = SimpleNamespace(
        storyline_md="# Timing",
        project_brief_md="# Project Brief\n\n## Business Context\n\nTiming.\n",
    )

    class StubGithubClient:
        async def create_empty_repo(
            self, *, owner, repo_name, private=True, default_branch="main"
        ):
            return {
                "owner": {"login": owner},
                "name": repo_name,
                "full_name": f"{owner}/{repo_name}",
                "id": 901,
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
                "name": "codespace-91",
                "state": "available",
                "web_url": "https://codespace-91.github.dev",
            }

    with caplog.at_level(logging.INFO):
        result = await bootstrap_service.bootstrap_empty_candidate_repo(
            github_client=StubGithubClient(),
            candidate_session=candidate_session,
            trial=trial,
            scenario_version=scenario_version,
            task=None,
            repo_prefix="winoe-ws-",
            destination_owner="winoe-ai-repos",
        )

    assert result.codespace_name == "codespace-91"
    assert any(
        record.message == "github_workspace_bootstrap_started"
        and record.__dict__.get("trial_id") == 11
        and record.__dict__.get("candidate_session_id") == 91
        and record.__dict__.get("repo_full_name") == "winoe-ai-repos/winoe-ws-91"
        for record in caplog.records
    )
    assert any(
        record.message == "github_codespace_provisioned"
        and record.__dict__.get("codespace_name") == "codespace-91"
        and record.__dict__.get("codespace_state") == "available"
        and record.__dict__.get("codespace_url") == "https://codespace-91.github.dev"
        and record.__dict__.get("attempt") == 1
        for record in caplog.records
    )
    assert any(
        record.message == "github_workspace_bootstrap_completed"
        and record.__dict__.get("elapsed_ms") is not None
        and record.__dict__.get("bootstrap_commit_sha") == "commit-sha"
        for record in caplog.records
    )


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
