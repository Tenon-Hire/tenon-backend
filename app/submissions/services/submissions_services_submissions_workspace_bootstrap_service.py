"""Application module for submissions services submissions workspace bootstrap service workflows."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from app.integrations.github.client import GithubClient, GithubError
from app.shared.database.shared_database_models_model import CandidateSession, Task
from app.shared.utils.shared_utils_project_brief_service import (
    canonical_project_brief_markdown,
)
from app.submissions.services.submissions_services_submissions_workspace_records_service import (
    build_codespace_url,
)
from app.submissions.services.submissions_services_submissions_workspace_repo_state_service import (
    add_collaborator_if_needed,
)

logger = logging.getLogger(__name__)

_DEFAULT_BRANCH = "main"
_DEVCONTAINER_JSON = {
    "name": "Winoe Candidate Workspace",
    "image": "mcr.microsoft.com/devcontainers/universal:2",
    "customizations": {
        "vscode": {
            "extensions": [
                "github.vscode-github-actions",
            ]
        }
    },
    "postCreateCommand": "echo 'Candidate workspace ready'",
}
_GITIGNORE_TEXT = "\n".join(
    [
        ".DS_Store",
        ".env",
        ".vscode/",
        "node_modules/",
        "__pycache__/",
        "dist/",
        "build/",
        "coverage/",
        "evidence/",
        "",
    ]
)
_EVIDENCE_WORKFLOW_TEXT = """name: Evidence Capture
on:
  workflow_dispatch:
  push:
    branches:
      - main
jobs:
  capture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Capture evidence
        run: |
          mkdir -p evidence
          printf '%s\\n' 'Evidence capture placeholder' > evidence/README.txt
      - uses: actions/upload-artifact@v4
        with:
          name: evidence-capture
          path: evidence/
"""
_CODESPACE_RETRY_DELAY_SECONDS = 1


@dataclass(frozen=True, slots=True)
class BootstrapRepoResult:
    """Represent an empty repository bootstrap result."""

    template_repo_full_name: str | None
    repo_full_name: str
    default_branch: str
    repo_id: int | None
    bootstrap_commit_sha: str | None
    codespace_name: str | None
    codespace_state: str | None
    codespace_url: str | None


def build_candidate_repo_name(prefix: str, candidate_session: CandidateSession) -> str:
    """Return the deterministic invite repository name."""
    resolved_prefix = (prefix or "").strip()
    if not resolved_prefix:
        raise GithubError("Repository prefix is not configured")
    return f"{resolved_prefix}{candidate_session.id}"


def _project_brief_readme(
    *,
    trial,
    scenario_version,
    task: Task | None,
) -> str:
    project_brief_md = canonical_project_brief_markdown(
        scenario_version,
        trial_title=getattr(trial, "title", None),
        storyline_md=getattr(scenario_version, "storyline_md", None),
    )
    brief_lines = [f"# {trial.title}", "", project_brief_md.strip()]
    if task is not None and getattr(task, "title", None):
        brief_lines.extend(["", "## Task", "", str(task.title).strip()])
    storyline = (getattr(scenario_version, "storyline_md", "") or "").strip()
    if storyline:
        brief_lines.extend(["", "## Scenario Context", "", storyline])
    return "\n".join(brief_lines).strip() + "\n"


def _bootstrap_file_payloads(
    *,
    trial,
    scenario_version,
    task: Task | None,
) -> list[dict[str, Any]]:
    return [
        {
            "path": ".devcontainer/devcontainer.json",
            "content": json.dumps(_DEVCONTAINER_JSON, indent=2, sort_keys=True) + "\n",
            "mode": "100644",
            "type": "blob",
        },
        {
            "path": ".gitignore",
            "content": _GITIGNORE_TEXT,
            "mode": "100644",
            "type": "blob",
        },
        {
            "path": ".github/workflows/evidence-capture.yml",
            "content": _EVIDENCE_WORKFLOW_TEXT,
            "mode": "100644",
            "type": "blob",
        },
        {
            "path": "README.md",
            "content": _project_brief_readme(
                trial=trial, scenario_version=scenario_version, task=task
            ),
            "mode": "100644",
            "type": "blob",
        },
    ]


def _bootstrap_paths() -> list[str]:
    return [
        ".devcontainer/devcontainer.json",
        ".gitignore",
        ".github/workflows/evidence-capture.yml",
        "README.md",
    ]


def _elapsed_ms(start_time: float) -> int:
    return int((time.perf_counter() - start_time) * 1000)


def _log_bootstrap_event(event: str, **fields: Any) -> None:
    logger.info(event, extra=fields)


async def _ensure_bootstrap_actor_access(
    github_client: GithubClient,
    *,
    repo_full_name: str,
    trial_id: int | None,
    candidate_session_id: int | None,
) -> str | None:
    """Grant the authenticated GitHub actor access before Codespace creation."""
    get_authenticated_user_login = getattr(
        github_client, "get_authenticated_user_login", None
    )
    if not callable(get_authenticated_user_login):
        return None
    github_username = await get_authenticated_user_login()
    if not github_username:
        return None
    _log_bootstrap_event(
        "github_codespace_actor_access_requested",
        trial_id=trial_id,
        candidate_session_id=candidate_session_id,
        repo_full_name=repo_full_name,
        github_username=github_username,
    )
    await add_collaborator_if_needed(github_client, repo_full_name, github_username)
    _log_bootstrap_event(
        "github_codespace_actor_access_granted",
        trial_id=trial_id,
        candidate_session_id=candidate_session_id,
        repo_full_name=repo_full_name,
        github_username=github_username,
    )
    return github_username


async def _delete_repo_safely(github_client: GithubClient, repo_full_name: str) -> None:
    """Delete a repository best-effort during invite cleanup."""
    delete_repo = getattr(github_client, "delete_repo", None)
    if not callable(delete_repo):
        return
    try:
        await delete_repo(repo_full_name)
    except GithubError as exc:
        if exc.status_code not in {404, 422}:
            logger.warning(
                "github_repo_cleanup_failed",
                extra={
                    "repo_full_name": repo_full_name,
                    "status_code": exc.status_code,
                },
            )


async def _create_candidate_repo(
    *, github_client: GithubClient, owner: str, repo_name: str, default_branch: str
) -> dict[str, Any]:
    """Create the repo using the empty-repo API, with a legacy test-double fallback."""
    create_empty_repo = getattr(github_client, "create_empty_repo", None)
    if callable(create_empty_repo):
        return await create_empty_repo(
            owner=owner,
            repo_name=repo_name,
            private=True,
            default_branch=default_branch,
        )

    generate_repo_from_template = getattr(
        github_client, "generate_repo_from_template", None
    )
    if callable(generate_repo_from_template):
        return await generate_repo_from_template(
            template_full_name="legacy/empty-repo",
            new_repo_name=repo_name,
            owner=owner,
            private=True,
        )

    raise HTTPException(
        status_code=500,
        detail="GitHub client does not support empty repo creation",
    )


async def bootstrap_empty_candidate_repo(
    *,
    github_client: GithubClient,
    candidate_session: CandidateSession,
    trial,
    scenario_version,
    task: Task | None,
    repo_prefix: str,
    destination_owner: str | None,
    repo_name: str | None = None,
) -> BootstrapRepoResult:
    """Create or reuse an empty candidate repository and seed the brief files."""
    overall_started_at = time.perf_counter()
    resolved_owner = (destination_owner or "").strip()
    if not resolved_owner:
        raise GithubError("Destination GitHub org is not configured")
    resolved_repo_name = repo_name or build_candidate_repo_name(
        repo_prefix, candidate_session
    )
    repo_full_name = f"{resolved_owner}/{resolved_repo_name}"
    default_branch = _DEFAULT_BRANCH
    legacy_repo_compat = not callable(getattr(github_client, "create_empty_repo", None))
    repo_created = False
    trial_id = getattr(trial, "id", None)
    candidate_session_id = getattr(candidate_session, "id", None)

    _log_bootstrap_event(
        "github_workspace_bootstrap_started",
        trial_id=trial_id,
        candidate_session_id=candidate_session_id,
        repo_full_name=repo_full_name,
        default_branch=default_branch,
    )

    try:
        repo_created_started_at = time.perf_counter()
        repo = await _create_candidate_repo(
            github_client=github_client,
            owner=resolved_owner,
            repo_name=resolved_repo_name,
            default_branch=default_branch,
        )
        repo_created = True
        _log_bootstrap_event(
            "github_workspace_repo_created",
            trial_id=trial_id,
            candidate_session_id=candidate_session_id,
            repo_full_name=repo_full_name,
            elapsed_ms=_elapsed_ms(repo_created_started_at),
            repo_id=repo.get("id"),
        )
    except GithubError as exc:
        if exc.status_code != 422:
            raise
        repo = await github_client.get_repo(repo_full_name)

    repo_id = repo.get("id")
    default_branch = str(
        repo.get("default_branch") or repo.get("master_branch") or default_branch
    )
    branch_ref = f"heads/{default_branch}"
    existing_branch_sha: str | None = None
    try:
        branch_payload = await github_client.get_branch(repo_full_name, default_branch)
        existing_branch_sha = (
            branch_payload.get("commit", {}).get("sha")
            if isinstance(branch_payload, dict)
            else None
        )
    except GithubError:
        existing_branch_sha = None
    if legacy_repo_compat:
        bootstrap_sha = existing_branch_sha
        codespace_name = None
        codespace_state = None
        codespace_url = None
        _log_bootstrap_event(
            "github_workspace_bootstrap_completed",
            trial_id=trial_id,
            candidate_session_id=candidate_session_id,
            repo_full_name=repo_full_name,
            default_branch=default_branch,
            repo_id=repo_id,
            bootstrap_commit_sha=bootstrap_sha,
            codespace_name=codespace_name,
            codespace_state=codespace_state,
            codespace_url=codespace_url,
            legacy_repo_compat=True,
            elapsed_ms=_elapsed_ms(overall_started_at),
        )
        return BootstrapRepoResult(
            template_repo_full_name=None,
            repo_full_name=repo_full_name,
            default_branch=default_branch,
            repo_id=repo_id,
            bootstrap_commit_sha=bootstrap_sha,
            codespace_name=codespace_name,
            codespace_state=codespace_state,
            codespace_url=codespace_url,
        )

    bootstrap_needed = False
    for path in _bootstrap_paths():
        try:
            await github_client.get_file_contents(
                repo_full_name, path, ref=default_branch
            )
        except GithubError as exc:
            if exc.status_code in {404, 422}:
                bootstrap_needed = True
                break
            raise

    try:
        if bootstrap_needed:
            bootstrap_started_at = time.perf_counter()
            create_or_update_file = getattr(
                github_client, "create_or_update_file", None
            )
            if not existing_branch_sha and callable(create_or_update_file):
                await create_or_update_file(
                    repo_full_name,
                    "README.md",
                    content=_project_brief_readme(
                        trial=trial, scenario_version=scenario_version, task=task
                    ),
                    message="chore: initialize candidate repo",
                    branch=default_branch,
                )
                try:
                    branch_payload = await github_client.get_branch(
                        repo_full_name, default_branch
                    )
                    existing_branch_sha = (
                        branch_payload.get("commit", {}).get("sha")
                        if isinstance(branch_payload, dict)
                        else None
                    )
                except GithubError:
                    existing_branch_sha = None

            file_payloads = _bootstrap_file_payloads(
                trial=trial, scenario_version=scenario_version, task=task
            )
            create_blob = getattr(github_client, "create_blob", None)
            tree: list[dict[str, Any]] = []
            if callable(create_blob):
                for payload in file_payloads:
                    blob = await create_blob(
                        repo_full_name,
                        content=payload["content"],
                    )
                    tree.append(
                        {
                            "path": payload["path"],
                            "mode": payload["mode"],
                            "type": payload["type"],
                            "sha": blob["sha"],
                        }
                    )
            else:
                tree = [
                    {
                        "path": payload["path"],
                        "mode": payload["mode"],
                        "type": payload["type"],
                        "content": payload["content"],
                    }
                    for payload in file_payloads
                ]

            base_tree_sha = None
            get_commit = getattr(github_client, "get_commit", None)
            if existing_branch_sha and callable(get_commit):
                current_commit = await github_client.get_commit(
                    repo_full_name, existing_branch_sha
                )
                base_tree_sha = (
                    current_commit.get("tree", {}).get("sha")
                    if isinstance(current_commit, dict)
                    else None
                )

            tree_result = await github_client.create_tree(
                repo_full_name, tree=tree, base_tree=base_tree_sha
            )
            commit_parents = [existing_branch_sha] if existing_branch_sha else []
            commit_result = await github_client.create_commit(
                repo_full_name,
                message="chore: bootstrap candidate repo",
                tree=tree_result["sha"],
                parents=commit_parents,
            )
            if existing_branch_sha:
                await github_client.update_ref(
                    repo_full_name,
                    ref=branch_ref,
                    sha=commit_result["sha"],
                    force=True,
                )
            else:
                await github_client.create_ref(
                    repo_full_name,
                    ref=f"refs/{branch_ref}",
                    sha=commit_result["sha"],
                )
            bootstrap_sha = commit_result["sha"]
            _log_bootstrap_event(
                "github_workspace_repo_bootstrapped",
                trial_id=trial_id,
                candidate_session_id=candidate_session_id,
                repo_full_name=repo_full_name,
                elapsed_ms=_elapsed_ms(bootstrap_started_at),
                bootstrap_commit_sha=bootstrap_sha,
            )
        else:
            bootstrap_sha = existing_branch_sha

        await _ensure_bootstrap_actor_access(
            github_client,
            repo_full_name=repo_full_name,
            trial_id=trial_id,
            candidate_session_id=candidate_session_id,
        )

        codespace = None
        last_codespace_error: GithubError | None = None
        for attempt in range(7):
            codespace_attempt_started_at = time.perf_counter()
            try:
                codespace = await github_client.create_codespace(
                    repo_full_name,
                    ref=default_branch,
                    devcontainer_path=".devcontainer/devcontainer.json",
                )
                last_codespace_error = None
                _log_bootstrap_event(
                    "github_codespace_provision_attempt",
                    trial_id=trial_id,
                    candidate_session_id=candidate_session_id,
                    repo_full_name=repo_full_name,
                    attempt=attempt + 1,
                    elapsed_ms=_elapsed_ms(codespace_attempt_started_at),
                    status_code=None,
                    succeeded=True,
                )
                break
            except GithubError as exc:
                last_codespace_error = exc
                _log_bootstrap_event(
                    "github_codespace_provision_attempt",
                    trial_id=trial_id,
                    candidate_session_id=candidate_session_id,
                    repo_full_name=repo_full_name,
                    attempt=attempt + 1,
                    elapsed_ms=_elapsed_ms(codespace_attempt_started_at),
                    status_code=exc.status_code,
                    succeeded=False,
                    error_message=str(exc),
                )
                if exc.status_code not in {404, 422}:
                    raise
                if attempt < 6:
                    # GitHub codespace creation can lag briefly after the repo
                    # commit lands. Keep the retry window short so the invite
                    # request stays under the upstream timeout budget.
                    await asyncio.sleep(_CODESPACE_RETRY_DELAY_SECONDS)
        if codespace is None:
            assert last_codespace_error is not None
            if last_codespace_error.status_code in {404, 422}:
                logger.warning(
                    "github_codespace_provision_degraded",
                    extra={
                        "trial_id": trial_id,
                        "candidate_session_id": candidate_session_id,
                        "repo_full_name": repo_full_name,
                        "status_code": last_codespace_error.status_code,
                        "elapsed_ms": _elapsed_ms(overall_started_at),
                    },
                )
                codespace_name = None
                codespace_state = None
                codespace_url = build_codespace_url(repo_full_name)
            else:
                raise last_codespace_error
        else:
            codespace_name = str(codespace.get("name") or "").strip() or None
            codespace_state = str(codespace.get("state") or "").strip().lower() or None
            codespace_url = (
                str(codespace.get("web_url") or codespace.get("url") or "").strip()
                or None
            )
            _log_bootstrap_event(
                "github_codespace_provisioned",
                trial_id=trial_id,
                candidate_session_id=candidate_session_id,
                repo_full_name=repo_full_name,
                attempt=attempt + 1,
                elapsed_ms=_elapsed_ms(codespace_attempt_started_at),
                codespace_name=codespace_name,
                codespace_state=codespace_state,
                codespace_url=codespace_url,
            )

        result = BootstrapRepoResult(
            template_repo_full_name=None,
            repo_full_name=repo_full_name,
            default_branch=default_branch,
            repo_id=repo_id,
            bootstrap_commit_sha=bootstrap_sha,
            codespace_name=codespace_name,
            codespace_state=codespace_state,
            codespace_url=codespace_url,
        )
        _log_bootstrap_event(
            "github_workspace_bootstrap_completed",
            trial_id=trial_id,
            candidate_session_id=candidate_session_id,
            repo_full_name=repo_full_name,
            default_branch=default_branch,
            repo_id=repo_id,
            bootstrap_commit_sha=bootstrap_sha,
            codespace_name=codespace_name,
            codespace_state=codespace_state,
            codespace_url=codespace_url,
            elapsed_ms=_elapsed_ms(overall_started_at),
        )
        return result
    except Exception:
        if repo_created:
            await _delete_repo_safely(github_client, repo_full_name)
        raise


__all__ = [
    "BootstrapRepoResult",
    "build_candidate_repo_name",
    "bootstrap_empty_candidate_repo",
]
