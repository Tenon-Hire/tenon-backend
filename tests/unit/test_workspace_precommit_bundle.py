from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.core.errors import ApiError
from app.integrations.github.client import GithubError
from app.repositories.precommit_bundles import repository as precommit_repo
from app.repositories.precommit_bundles.models import PRECOMMIT_BUNDLE_STATUS_READY
from app.services.submissions import workspace_precommit_bundle as precommit_service
from app.services.submissions.workspace_precommit_bundle import (
    apply_precommit_bundle_if_available,
    build_precommit_commit_marker,
)
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


class StubGithubClient:
    def __init__(self, *, commits: list[dict] | None = None) -> None:
        self._commits = commits or []
        self.created_blobs: list[tuple[str, str]] = []
        self.created_trees: list[tuple[list[dict], str | None]] = []
        self.created_commits: list[tuple[str, str, list[str]]] = []
        self.updated_refs: list[tuple[str, str, bool]] = []

    async def list_commits(
        self, repo_full_name: str, *, sha: str | None = None, per_page: int = 30
    ) -> list[dict]:
        return list(self._commits)

    async def get_ref(self, repo_full_name: str, ref: str) -> dict:
        return {"ref": ref, "object": {"sha": "head-sha"}}

    async def get_commit(self, repo_full_name: str, commit_sha: str) -> dict:
        return {"sha": commit_sha, "tree": {"sha": "base-tree-sha"}}

    async def create_blob(
        self,
        repo_full_name: str,
        *,
        content: str,
        encoding: str = "utf-8",
    ) -> dict:
        self.created_blobs.append((content, encoding))
        return {"sha": f"blob-{len(self.created_blobs)}"}

    async def create_tree(
        self,
        repo_full_name: str,
        *,
        tree: list[dict],
        base_tree: str | None = None,
    ) -> dict:
        self.created_trees.append((tree, base_tree))
        return {"sha": "new-tree-sha"}

    async def create_commit(
        self,
        repo_full_name: str,
        *,
        message: str,
        tree: str,
        parents: list[str],
    ) -> dict:
        self.created_commits.append((message, tree, parents))
        return {"sha": "new-commit-sha"}

    async def update_ref(
        self,
        repo_full_name: str,
        *,
        ref: str,
        sha: str,
        force: bool = False,
    ) -> dict:
        self.updated_refs.append((ref, sha, force))
        return {"ref": ref, "object": {"sha": sha}}


@pytest.mark.asyncio
async def test_apply_precommit_bundle_success(async_session):
    recruiter = await create_recruiter(async_session, email="bundle-apply@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
    )
    scenario_version_id = candidate_session.scenario_version_id
    assert scenario_version_id is not None

    bundle = await precommit_repo.create_bundle(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
        status=PRECOMMIT_BUNDLE_STATUS_READY,
        patch_text=json.dumps(
            {
                "files": [
                    {"path": "README.md", "content": "# Baseline\n"},
                    {
                        "path": "scripts/setup.sh",
                        "content": "#!/usr/bin/env bash\necho setup\n",
                        "executable": True,
                    },
                ]
            }
        ),
        base_template_sha="base-sha-123",
    )
    github_client = StubGithubClient()

    result = await apply_precommit_bundle_if_available(
        async_session,
        github_client=github_client,
        candidate_session=candidate_session,
        task=tasks[1],
        repo_full_name="org/workspace-repo",
        default_branch="main",
        base_template_sha="base-sha-123",
        existing_precommit_sha=None,
    )

    assert result.state == "applied"
    assert result.precommit_sha == "new-commit-sha"
    assert result.bundle_id == bundle.id
    assert len(github_client.created_blobs) == 2
    assert len(github_client.created_trees) == 1
    assert len(github_client.created_commits) == 1
    assert github_client.updated_refs == [("heads/main", "new-commit-sha", False)]
    commit_message = github_client.created_commits[0][0]
    assert (
        build_precommit_commit_marker(bundle.id, bundle.content_sha256)
        in commit_message
    )


@pytest.mark.asyncio
async def test_apply_precommit_bundle_does_not_mutate_bundle_applied_commit_sha(
    async_session,
):
    recruiter = await create_recruiter(async_session, email="bundle-semantics@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
    )
    scenario_version_id = candidate_session.scenario_version_id
    assert scenario_version_id is not None

    bundle = await precommit_repo.create_bundle(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
        status=PRECOMMIT_BUNDLE_STATUS_READY,
        patch_text=json.dumps(
            {"files": [{"path": "README.md", "content": "# Baseline\n"}]}
        ),
        applied_commit_sha=None,
    )
    github_client = StubGithubClient()

    result = await apply_precommit_bundle_if_available(
        async_session,
        github_client=github_client,
        candidate_session=candidate_session,
        task=tasks[1],
        repo_full_name="org/workspace-repo",
        default_branch="main",
        base_template_sha="base-sha-123",
        existing_precommit_sha=None,
    )
    await async_session.refresh(bundle)

    assert result.state == "applied"
    assert result.precommit_sha == "new-commit-sha"
    assert bundle.applied_commit_sha is None


@pytest.mark.asyncio
async def test_apply_precommit_bundle_idempotent_when_marker_commit_exists(
    async_session,
):
    recruiter = await create_recruiter(async_session, email="bundle-marker@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
    )
    scenario_version_id = candidate_session.scenario_version_id
    assert scenario_version_id is not None

    bundle = await precommit_repo.create_bundle(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
        status=PRECOMMIT_BUNDLE_STATUS_READY,
        patch_text=json.dumps(
            {"files": [{"path": "README.md", "content": "# Baseline\n"}]}
        ),
    )
    marker = build_precommit_commit_marker(bundle.id, bundle.content_sha256)
    github_client = StubGithubClient(
        commits=[
            {
                "sha": "existing-precommit-sha",
                "commit": {
                    "message": f"chore(tenon): apply scenario scaffolding\n\n{marker}"
                },
            }
        ]
    )

    result = await apply_precommit_bundle_if_available(
        async_session,
        github_client=github_client,
        candidate_session=candidate_session,
        task=tasks[1],
        repo_full_name="org/workspace-repo",
        default_branch="main",
        base_template_sha="base-sha-123",
        existing_precommit_sha=None,
    )

    assert result.state == "already_applied"
    assert result.precommit_sha == "existing-precommit-sha"
    assert github_client.created_blobs == []
    assert github_client.created_trees == []
    assert github_client.created_commits == []
    assert github_client.updated_refs == []


@pytest.mark.asyncio
async def test_apply_precommit_bundle_rejects_unsafe_paths(async_session):
    recruiter = await create_recruiter(async_session, email="bundle-unsafe@test.com")
    sim, tasks = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=sim,
        status="in_progress",
    )
    scenario_version_id = candidate_session.scenario_version_id
    assert scenario_version_id is not None

    await precommit_repo.create_bundle(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
        status=PRECOMMIT_BUNDLE_STATUS_READY,
        patch_text=json.dumps(
            {"files": [{"path": "../secrets.env", "content": "SHOULD_NOT_APPLY=1\n"}]}
        ),
    )
    github_client = StubGithubClient()

    with pytest.raises(ApiError) as excinfo:
        await apply_precommit_bundle_if_available(
            async_session,
            github_client=github_client,
            candidate_session=candidate_session,
            task=tasks[1],
            repo_full_name="org/workspace-repo",
            default_branch="main",
            base_template_sha="base-sha-123",
            existing_precommit_sha=None,
        )

    assert excinfo.value.error_code == "PRECOMMIT_PATCH_UNSAFE_PATH"


@pytest.mark.asyncio
async def test_apply_precommit_bundle_skips_when_workspace_already_has_precommit():
    result = await apply_precommit_bundle_if_available(
        object(),
        github_client=StubGithubClient(),
        candidate_session=SimpleNamespace(id=1, scenario_version_id=2),
        task=SimpleNamespace(id=3, type="code"),
        repo_full_name="org/workspace-repo",
        default_branch="main",
        base_template_sha="base-sha",
        existing_precommit_sha="already-sha",
    )
    assert result.state == "already_applied"
    assert result.precommit_sha == "already-sha"


@pytest.mark.asyncio
async def test_apply_precommit_bundle_skips_non_code_and_missing_scenario():
    non_code = await apply_precommit_bundle_if_available(
        object(),
        github_client=StubGithubClient(),
        candidate_session=SimpleNamespace(id=1, scenario_version_id=2),
        task=SimpleNamespace(id=3, type="design"),
        repo_full_name="org/workspace-repo",
        default_branch="main",
        base_template_sha="base-sha",
        existing_precommit_sha=None,
    )
    assert non_code.state == "no_bundle"

    missing_scenario = await apply_precommit_bundle_if_available(
        object(),
        github_client=StubGithubClient(),
        candidate_session=SimpleNamespace(id=1, scenario_version_id=None),
        task=SimpleNamespace(id=3, type="code"),
        repo_full_name="org/workspace-repo",
        default_branch="main",
        base_template_sha="base-sha",
        existing_precommit_sha=None,
    )
    assert missing_scenario.state == "no_bundle"


@pytest.mark.asyncio
async def test_apply_precommit_bundle_skips_when_scenario_template_key_missing(
    monkeypatch,
):
    async def _scenario_missing_template(_db, _scenario_version_id):
        return SimpleNamespace(template_key="")

    monkeypatch.setattr(
        precommit_service.scenario_repo, "get_by_id", _scenario_missing_template
    )
    result = await apply_precommit_bundle_if_available(
        object(),
        github_client=StubGithubClient(),
        candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
        task=SimpleNamespace(id=3, type="code"),
        repo_full_name="org/workspace-repo",
        default_branch="main",
        base_template_sha="base-sha",
        existing_precommit_sha=None,
    )
    assert result.state == "no_bundle"


@pytest.mark.asyncio
async def test_apply_precommit_bundle_errors_for_base_sha_mismatch(monkeypatch):
    async def _scenario(_db, _scenario_version_id):
        return SimpleNamespace(template_key="template-default")

    async def _bundle(_db, scenario_version_id: int, template_key: str):
        return SimpleNamespace(
            id=9,
            content_sha256="abc",
            base_template_sha="expected-base-sha",
            patch_text=json.dumps(
                {"files": [{"path": "README.md", "content": "# baseline\n"}]}
            ),
            storage_ref=None,
        )

    monkeypatch.setattr(precommit_service.scenario_repo, "get_by_id", _scenario)
    monkeypatch.setattr(
        precommit_service.bundle_repo, "get_ready_by_scenario_and_template", _bundle
    )

    with pytest.raises(ApiError) as excinfo:
        await apply_precommit_bundle_if_available(
            object(),
            github_client=StubGithubClient(),
            candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
            task=SimpleNamespace(id=3, type="code"),
            repo_full_name="org/workspace-repo",
            default_branch="main",
            base_template_sha="different-base-sha",
            existing_precommit_sha=None,
        )
    assert excinfo.value.error_code == "PRECOMMIT_BASE_SHA_MISMATCH"


@pytest.mark.asyncio
async def test_apply_precommit_bundle_errors_for_empty_changes(monkeypatch):
    async def _scenario(_db, _scenario_version_id):
        return SimpleNamespace(template_key="template-default")

    async def _bundle(_db, scenario_version_id: int, template_key: str):
        return SimpleNamespace(
            id=10,
            content_sha256="abc",
            base_template_sha="base-sha",
            patch_text=json.dumps({"files": []}),
            storage_ref=None,
        )

    monkeypatch.setattr(precommit_service.scenario_repo, "get_by_id", _scenario)
    monkeypatch.setattr(
        precommit_service.bundle_repo, "get_ready_by_scenario_and_template", _bundle
    )

    with pytest.raises(ApiError) as excinfo:
        await apply_precommit_bundle_if_available(
            object(),
            github_client=StubGithubClient(),
            candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
            task=SimpleNamespace(id=3, type="code"),
            repo_full_name="org/workspace-repo",
            default_branch="main",
            base_template_sha="base-sha",
            existing_precommit_sha=None,
        )
    assert excinfo.value.error_code == "PRECOMMIT_BUNDLE_EMPTY"


class _BranchFailureGithub(StubGithubClient):
    def __init__(
        self,
        *,
        ref_sha: str = "head-sha",
        tree_sha: str = "base-tree-sha",
        blob_sha: str = "blob-1",
        commit_sha: str = "new-commit-sha",
        raise_update: GithubError | None = None,
        commits: list[dict] | None = None,
        commits_by_call: list[list[dict]] | None = None,
    ) -> None:
        super().__init__(commits=commits)
        self._ref_sha = ref_sha
        self._tree_sha = tree_sha
        self._blob_sha = blob_sha
        self._commit_sha = commit_sha
        self._raise_update = raise_update
        self._commits_by_call = commits_by_call
        self._commit_lookup_calls = 0

    async def list_commits(
        self, repo_full_name: str, *, sha: str | None = None, per_page: int = 30
    ) -> list[dict]:
        self._commit_lookup_calls += 1
        if self._commits_by_call is not None:
            idx = self._commit_lookup_calls - 1
            if idx < len(self._commits_by_call):
                return list(self._commits_by_call[idx])
            return []
        return await super().list_commits(repo_full_name, sha=sha, per_page=per_page)

    async def get_ref(self, repo_full_name: str, ref: str) -> dict:
        return {"ref": ref, "object": {"sha": self._ref_sha}}

    async def get_commit(self, repo_full_name: str, commit_sha: str) -> dict:
        return {"sha": commit_sha, "tree": {"sha": self._tree_sha}}

    async def create_blob(
        self,
        repo_full_name: str,
        *,
        content: str,
        encoding: str = "utf-8",
    ) -> dict:
        self.created_blobs.append((content, encoding))
        return {"sha": self._blob_sha}

    async def create_tree(
        self,
        repo_full_name: str,
        *,
        tree: list[dict],
        base_tree: str | None = None,
    ) -> dict:
        return {"sha": "new-tree-sha"}

    async def create_commit(
        self,
        repo_full_name: str,
        *,
        message: str,
        tree: str,
        parents: list[str],
    ) -> dict:
        return {"sha": self._commit_sha}

    async def update_ref(
        self,
        repo_full_name: str,
        *,
        ref: str,
        sha: str,
        force: bool = False,
    ) -> dict:
        if self._raise_update is not None:
            raise self._raise_update
        return {"ref": ref, "object": {"sha": sha}}


@pytest.mark.asyncio
async def test_apply_precommit_bundle_errors_for_missing_git_data(monkeypatch):
    async def _scenario(_db, _scenario_version_id):
        return SimpleNamespace(template_key="template-default")

    async def _bundle(_db, scenario_version_id: int, template_key: str):
        return SimpleNamespace(
            id=11,
            content_sha256="abc",
            base_template_sha=None,
            patch_text=json.dumps(
                {"files": [{"path": "README.md", "content": "# baseline\n"}]}
            ),
            storage_ref=None,
        )

    monkeypatch.setattr(precommit_service.scenario_repo, "get_by_id", _scenario)
    monkeypatch.setattr(
        precommit_service.bundle_repo, "get_ready_by_scenario_and_template", _bundle
    )

    with pytest.raises(ApiError) as missing_head:
        await apply_precommit_bundle_if_available(
            object(),
            github_client=_BranchFailureGithub(ref_sha=""),
            candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
            task=SimpleNamespace(id=3, type="code"),
            repo_full_name="org/workspace-repo",
            default_branch="main",
            base_template_sha="base-sha",
            existing_precommit_sha=None,
        )
    assert missing_head.value.error_code == "PRECOMMIT_REPO_HEAD_MISSING"

    with pytest.raises(ApiError) as missing_tree:
        await apply_precommit_bundle_if_available(
            object(),
            github_client=_BranchFailureGithub(tree_sha=""),
            candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
            task=SimpleNamespace(id=3, type="code"),
            repo_full_name="org/workspace-repo",
            default_branch="main",
            base_template_sha="base-sha",
            existing_precommit_sha=None,
        )
    assert missing_tree.value.error_code == "PRECOMMIT_REPO_TREE_MISSING"

    with pytest.raises(ApiError) as missing_blob:
        await apply_precommit_bundle_if_available(
            object(),
            github_client=_BranchFailureGithub(blob_sha=""),
            candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
            task=SimpleNamespace(id=3, type="code"),
            repo_full_name="org/workspace-repo",
            default_branch="main",
            base_template_sha="base-sha",
            existing_precommit_sha=None,
        )
    assert missing_blob.value.error_code == "PRECOMMIT_BLOB_CREATE_FAILED"

    class _MissingTreeSha(_BranchFailureGithub):
        async def create_tree(
            self,
            repo_full_name: str,
            *,
            tree: list[dict],
            base_tree: str | None = None,
        ) -> dict:
            return {"sha": ""}

    with pytest.raises(ApiError) as missing_tree_sha:
        await apply_precommit_bundle_if_available(
            object(),
            github_client=_MissingTreeSha(),
            candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
            task=SimpleNamespace(id=3, type="code"),
            repo_full_name="org/workspace-repo",
            default_branch="main",
            base_template_sha="base-sha",
            existing_precommit_sha=None,
        )
    assert missing_tree_sha.value.error_code == "PRECOMMIT_TREE_CREATE_FAILED"

    with pytest.raises(ApiError) as missing_commit_sha:
        await apply_precommit_bundle_if_available(
            object(),
            github_client=_BranchFailureGithub(commit_sha=""),
            candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
            task=SimpleNamespace(id=3, type="code"),
            repo_full_name="org/workspace-repo",
            default_branch="main",
            base_template_sha="base-sha",
            existing_precommit_sha=None,
        )
    assert missing_commit_sha.value.error_code == "PRECOMMIT_COMMIT_CREATE_FAILED"


@pytest.mark.asyncio
async def test_apply_precommit_bundle_recovers_after_ref_conflict(monkeypatch):
    async def _scenario(_db, _scenario_version_id):
        return SimpleNamespace(template_key="template-default")

    async def _bundle(_db, scenario_version_id: int, template_key: str):
        return SimpleNamespace(
            id=12,
            content_sha256="abc",
            base_template_sha=None,
            patch_text=json.dumps(
                {"files": [{"path": "README.md", "content": "# baseline\n"}]}
            ),
            storage_ref=None,
        )

    marker = precommit_service.build_precommit_commit_marker(12, "abc")
    github_client = _BranchFailureGithub(
        raise_update=GithubError("conflict", status_code=422),
        commits_by_call=[
            [],
            [{"sha": "recovered-sha", "commit": {"message": f"x\n\n{marker}"}}],
        ],
    )
    monkeypatch.setattr(precommit_service.scenario_repo, "get_by_id", _scenario)
    monkeypatch.setattr(
        precommit_service.bundle_repo, "get_ready_by_scenario_and_template", _bundle
    )

    result = await apply_precommit_bundle_if_available(
        object(),
        github_client=github_client,
        candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
        task=SimpleNamespace(id=3, type="code"),
        repo_full_name="org/workspace-repo",
        default_branch="main",
        base_template_sha="base-sha",
        existing_precommit_sha=None,
    )
    assert result.state == "already_applied"
    assert result.precommit_sha == "recovered-sha"


@pytest.mark.asyncio
async def test_apply_precommit_bundle_ref_conflict_without_marker_reraises(monkeypatch):
    async def _scenario(_db, _scenario_version_id):
        return SimpleNamespace(template_key="template-default")

    async def _bundle(_db, scenario_version_id: int, template_key: str):
        return SimpleNamespace(
            id=12,
            content_sha256="abc",
            base_template_sha=None,
            patch_text=json.dumps(
                {"files": [{"path": "README.md", "content": "# baseline\n"}]}
            ),
            storage_ref=None,
        )

    github_client = _BranchFailureGithub(
        raise_update=GithubError("conflict", status_code=422),
        commits_by_call=[[], []],
    )
    monkeypatch.setattr(precommit_service.scenario_repo, "get_by_id", _scenario)
    monkeypatch.setattr(
        precommit_service.bundle_repo, "get_ready_by_scenario_and_template", _bundle
    )

    with pytest.raises(GithubError) as excinfo:
        await apply_precommit_bundle_if_available(
            object(),
            github_client=github_client,
            candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
            task=SimpleNamespace(id=3, type="code"),
            repo_full_name="org/workspace-repo",
            default_branch="main",
            base_template_sha="base-sha",
            existing_precommit_sha=None,
        )
    assert excinfo.value.status_code == 422


@pytest.mark.asyncio
async def test_apply_precommit_bundle_propagates_ref_update_errors(monkeypatch):
    async def _scenario(_db, _scenario_version_id):
        return SimpleNamespace(template_key="template-default")

    async def _bundle(_db, scenario_version_id: int, template_key: str):
        return SimpleNamespace(
            id=13,
            content_sha256="abc",
            base_template_sha=None,
            patch_text=json.dumps(
                {"files": [{"path": "README.md", "content": "# baseline\n"}]}
            ),
            storage_ref=None,
        )

    github_client = _BranchFailureGithub(
        raise_update=GithubError("hard-failure", status_code=500),
        commits_by_call=[[]],
    )
    monkeypatch.setattr(precommit_service.scenario_repo, "get_by_id", _scenario)
    monkeypatch.setattr(
        precommit_service.bundle_repo, "get_ready_by_scenario_and_template", _bundle
    )

    with pytest.raises(GithubError) as excinfo:
        await apply_precommit_bundle_if_available(
            object(),
            github_client=github_client,
            candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
            task=SimpleNamespace(id=3, type="code"),
            repo_full_name="org/workspace-repo",
            default_branch="main",
            base_template_sha="base-sha",
            existing_precommit_sha=None,
        )
    assert excinfo.value.status_code == 500


@pytest.mark.asyncio
async def test_apply_precommit_bundle_handles_delete_entries(monkeypatch):
    async def _scenario(_db, _scenario_version_id):
        return SimpleNamespace(template_key="template-default")

    async def _bundle(_db, scenario_version_id: int, template_key: str):
        return SimpleNamespace(
            id=14,
            content_sha256="abc",
            base_template_sha=None,
            patch_text=json.dumps(
                {"files": [{"path": "obsolete.txt", "delete": True}]}
            ),
            storage_ref=None,
        )

    github_client = _BranchFailureGithub(commits_by_call=[[]])
    monkeypatch.setattr(precommit_service.scenario_repo, "get_by_id", _scenario)
    monkeypatch.setattr(
        precommit_service.bundle_repo, "get_ready_by_scenario_and_template", _bundle
    )

    result = await apply_precommit_bundle_if_available(
        object(),
        github_client=github_client,
        candidate_session=SimpleNamespace(id=1, scenario_version_id=22),
        task=SimpleNamespace(id=3, type="code"),
        repo_full_name="org/workspace-repo",
        default_branch="main",
        base_template_sha="base-sha",
        existing_precommit_sha=None,
    )
    assert result.state == "applied"
    assert github_client.created_blobs == []


def test_parse_patch_entries_and_path_guards():
    assert (
        precommit_service._parse_patch_entries(
            patch_text=json.dumps({"files": [{"path": "a.txt", "delete": True}]}),
            storage_ref=None,
        )[0].delete
        is True
    )

    with pytest.raises(ApiError) as storage_only:
        precommit_service._parse_patch_entries(patch_text=None, storage_ref="ref:abc")
    assert storage_only.value.error_code == "PRECOMMIT_STORAGE_REF_UNSUPPORTED"

    with pytest.raises(ApiError) as invalid_json:
        precommit_service._parse_patch_entries(patch_text="{not-json", storage_ref=None)
    assert invalid_json.value.error_code == "PRECOMMIT_PATCH_INVALID_JSON"

    with pytest.raises(ApiError) as invalid_format:
        precommit_service._parse_patch_entries(
            patch_text=json.dumps({"files": {"path": "x"}}),
            storage_ref=None,
        )
    assert invalid_format.value.error_code == "PRECOMMIT_PATCH_INVALID_FORMAT"

    with pytest.raises(ApiError) as invalid_entry:
        precommit_service._parse_patch_entries(
            patch_text=json.dumps({"files": [123]}),
            storage_ref=None,
        )
    assert invalid_entry.value.error_code == "PRECOMMIT_PATCH_INVALID_ENTRY"

    with pytest.raises(ApiError) as invalid_path:
        precommit_service._parse_patch_entries(
            patch_text=json.dumps({"files": [{"path": 42, "content": "x"}]}),
            storage_ref=None,
        )
    assert invalid_path.value.error_code == "PRECOMMIT_PATCH_INVALID_PATH"

    with pytest.raises(ApiError) as invalid_content:
        precommit_service._parse_patch_entries(
            patch_text=json.dumps({"files": [{"path": "a.txt", "content": 42}]}),
            storage_ref=None,
        )
    assert invalid_content.value.error_code == "PRECOMMIT_PATCH_INVALID_CONTENT"

    for bad_path in ("", "\\bad\\path", "a//b", ".git/config"):
        with pytest.raises(ApiError) as bad_path_error:
            precommit_service._ensure_safe_repo_path(bad_path)
        assert bad_path_error.value.error_code == "PRECOMMIT_PATCH_UNSAFE_PATH"


@pytest.mark.asyncio
async def test_find_marker_commit_sha_skips_non_match_and_blank_sha():
    marker = "tenon-marker"
    client = _BranchFailureGithub(
        commits=[
            {"sha": "", "commit": {"message": f"contains {marker} but blank sha"}},
            {"sha": "non-marker-sha", "commit": {"message": "no match here"}},
        ]
    )

    resolved = await precommit_service._find_marker_commit_sha(
        client,
        repo_full_name="org/workspace-repo",
        branch="main",
        marker=marker,
    )
    assert resolved is None
