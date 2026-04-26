"""Application module for submissions services submissions workspace bootstrap service workflows."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from textwrap import dedent
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
    ensure_repo_is_active,
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
        "Thumbs.db",
        ".idea/",
        ".vscode/",
        ".history/",
        ".env",
        ".env.*",
        "*.local",
        "*.log",
        "node_modules/",
        ".npm/",
        "__pycache__/",
        "*.pyc",
        ".pytest_cache/",
        ".ruff_cache/",
        ".mypy_cache/",
        ".tox/",
        ".venv/",
        "venv/",
        "dist/",
        "build/",
        "coverage/",
        ".coverage",
        ".coverage.*",
        "evidence/",
        "target/",
        "bin/",
        "obj/",
        "out/",
        "release/",
        "debug/",
        "tmp/",
        "temp/",
        "",
    ]
)
_CODESPACE_RETRY_DELAY_SECONDS = 1
_EVIDENCE_WORKFLOW_PATH = ".github/workflows/winoe-evidence-capture.yml"


def build_evidence_capture_workflow_yaml() -> str:
    """Return the seeded evidence-capture workflow content."""
    return (
        dedent(
            """\
        name: Winoe Evidence Capture

        on:
          push:
          workflow_dispatch:

        permissions:
          contents: read

        jobs:
          capture:
            runs-on: ubuntu-latest
            steps:
              - name: Check out repository
                uses: actions/checkout@v4
                with:
                  fetch-depth: 0

              - name: Capture evidence
                continue-on-error: true
                run: |
                  python - <<'PY'
                  import json
                  import os
                  import pathlib
                  import subprocess
                  from collections import Counter
                  from datetime import UTC, datetime

                  artifacts = pathlib.Path("artifacts")
                  artifacts.mkdir(parents=True, exist_ok=True)
                  repo_root = pathlib.Path(".")
                  generated_at = datetime.now(UTC).isoformat()
                  repository_full_name = os.environ.get("GITHUB_REPOSITORY")
                  commit_sha = os.environ.get("GITHUB_SHA")
                  workflow_run_id = os.environ.get("GITHUB_RUN_ID")
                  schema_version = "1"
                  written: list[dict[str, object]] = []

                  def run_git(*args: str) -> subprocess.CompletedProcess[str]:
                      return subprocess.run(
                          ["git", *args],
                          capture_output=True,
                          text=True,
                          check=False,
                      )

                  def write_json(name: str, status: str, payload: object) -> dict[str, object]:
                      record = {
                          "schema_version": schema_version,
                          "repository_full_name": repository_full_name,
                          "commit_sha": commit_sha,
                          "workflow_run_id": workflow_run_id,
                          "generated_at": generated_at,
                          "status": status,
                          "payload": payload,
                      }
                      (artifacts / name).write_text(
                          json.dumps(record, indent=2, sort_keys=True) + "\\n",
                          encoding="utf-8",
                      )
                      written.append({"name": name, "status": status})
                      return record

                  def trunc(text: str | None, limit: int = 20000) -> str:
                      if not text:
                          return ""
                      return text[:limit]

                  def detect_manifests() -> list[dict[str, object]]:
                      manifests: list[dict[str, object]] = []
                      package_path = repo_root / "package.json"
                      if package_path.exists():
                          try:
                              package_data = json.loads(package_path.read_text(encoding="utf-8"))
                          except ValueError:
                              package_data = {}
                          scripts = package_data.get("scripts") if isinstance(package_data, dict) else {}
                          has_test_script = isinstance(scripts, dict) and "test" in scripts
                          has_lint_script = isinstance(scripts, dict) and "lint" in scripts
                          manifests.append(
                              {
                                  "path": "package.json",
                                  "kind": "node",
                                  "test_command": "npm test" if has_test_script else None,
                                  "lint_command": "npm run lint" if has_lint_script else None,
                                  "reason": (
                                      "detected package.json scripts"
                                      if has_test_script or has_lint_script
                                      else "package.json found without test or lint scripts"
                                  ),
                              }
                          )
                      python_manifest = None
                      if (repo_root / "pyproject.toml").exists():
                          python_manifest = "pyproject.toml"
                      elif (repo_root / "requirements.txt").exists():
                          python_manifest = "requirements.txt"
                      if python_manifest is not None:
                          test_paths = [
                              "tests",
                              "test",
                              "spec",
                          ]
                          has_common_tests = any((repo_root / path).exists() for path in test_paths)
                          manifests.append(
                              {
                                  "path": python_manifest,
                                  "kind": "python",
                                  "test_command": "python -m pytest" if has_common_tests else None,
                                  "lint_command": "python -m ruff check .",
                                  "reason": (
                                      "detected Python project manifest and common test paths"
                                      if has_common_tests
                                      else "detected Python project manifest without obvious test paths"
                                  ),
                              }
                          )
                      if (repo_root / "go.mod").exists():
                          manifests.append(
                              {
                                  "path": "go.mod",
                                  "kind": "go",
                                  "test_command": "go test ./...",
                                  "lint_command": "golangci-lint run",
                              }
                          )
                      if (repo_root / "pom.xml").exists():
                          manifests.append(
                              {
                                  "path": "pom.xml",
                                  "kind": "maven",
                                  "test_command": "mvn test",
                                  "lint_command": "mvn -q -DskipTests checkstyle:check",
                              }
                          )
                      if (repo_root / "Cargo.toml").exists():
                          manifests.append(
                              {
                                  "path": "Cargo.toml",
                                  "kind": "rust",
                                  "test_command": "cargo test",
                                  "lint_command": "cargo clippy -- -D warnings",
                              }
                          )
                      return manifests

                  def choose_command(manifests: list[dict[str, object]], key: str) -> dict[str, object]:
                      for manifest in manifests:
                          command = manifest.get(key)
                          if isinstance(command, str) and command.strip():
                              return {
                                  "detected": True,
                                  "tool": manifest.get("kind"),
                                  "command": command,
                                  "manifest_path": manifest.get("path"),
                                  "reason": f"detected from {manifest.get('path')}",
                              }
                      return {
                          "detected": False,
                          "tool": None,
                          "command": None,
                          "manifest_path": None,
                          "reason": "no supported manifest with a runnable command found",
                      }

                  def run_command(command: str | None) -> dict[str, object]:
                      if not command:
                          return {
                              "status": "not_detected",
                              "command": None,
                              "exit_code": None,
                              "stdout": "",
                              "stderr": "",
                          }
                      proc = subprocess.run(
                          command,
                          shell=True,
                          capture_output=True,
                          text=True,
                          check=False,
                      )
                      return {
                          "status": "success" if proc.returncode == 0 else "failed",
                          "command": command,
                          "exit_code": proc.returncode,
                          "stdout": trunc(proc.stdout),
                          "stderr": trunc(proc.stderr),
                      }

                  head = run_git("rev-parse", "HEAD")
                  head_sha = head.stdout.strip() if head.returncode == 0 else commit_sha
                  rev_list = run_git("rev-list", "--reverse", "HEAD")
                  commits: list[dict[str, object]] = []
                  if rev_list.returncode == 0:
                      for sha in rev_list.stdout.splitlines():
                          show = run_git(
                              "show",
                              "--date=iso-strict",
                              "--format=%H%x09%ad%x09%s",
                              "--numstat",
                              "--no-renames",
                              sha,
                          )
                          if show.returncode != 0 or not show.stdout.strip():
                              commits.append({"sha": sha, "error": "git show failed"})
                              continue
                          lines = show.stdout.splitlines()
                          commit_line = lines[0].split("\t", 2)
                          if len(commit_line) != 3:
                              commits.append({"sha": sha, "error": "unexpected git show output"})
                              continue
                          commit_sha_value, timestamp, message = commit_line
                          files_changed: list[str] = []
                          insertions = 0
                          deletions = 0
                          for line in lines[1:]:
                              if not line.strip():
                                  continue
                              parts = line.split("\t")
                              if len(parts) != 3:
                                  continue
                              added, removed, path = parts
                              files_changed.append(path)
                              if added != "-":
                                  insertions += int(added)
                              if removed != "-":
                                  deletions += int(removed)
                          commits.append(
                              {
                                  "sha": commit_sha_value,
                                  "timestamp": timestamp,
                                  "message": message,
                                  "files_changed": files_changed,
                                  "files_changed_count": len(files_changed),
                                  "insertions": insertions,
                                  "deletions": deletions,
                              }
                          )

                  creation_log = run_git(
                      "log",
                      "--reverse",
                      "--diff-filter=A",
                      "--date=iso-strict",
                      "--format=%H%x09%ad%x09%s",
                      "--name-only",
                      "--no-renames",
                  )
                  creation_events: list[dict[str, object]] = []
                  current_event: dict[str, object] | None = None
                  if creation_log.returncode == 0:
                      for line in creation_log.stdout.splitlines():
                          if not line.strip():
                              current_event = None
                              continue
                          if current_event is None and line.count("\t") >= 2:
                              commit_sha_value, timestamp, message = line.split("\t", 2)
                              current_event = {
                                  "commit_sha": commit_sha_value,
                                  "timestamp": timestamp,
                                  "message": message,
                                  "files": [],
                              }
                              creation_events.append(current_event)
                              continue
                          if current_event is not None:
                              files = current_event.setdefault("files", [])
                              if isinstance(files, list):
                                  files.append(line.strip())

                  tree_files = [path for path in run_git("ls-files").stdout.splitlines() if path.strip()]
                  dir_counts: Counter[str] = Counter()
                  extension_counts: Counter[str] = Counter()
                  for path in tree_files:
                      normalized = pathlib.PurePosixPath(path)
                      parent = normalized.parent.as_posix()
                      dir_counts[parent if parent != "." else "."] += 1
                      extension = normalized.suffix.lower() or "[no extension]"
                      extension_counts[extension] += 1

                  manifests = detect_manifests()
                  test_detection = choose_command(manifests, "test_command")
                  lint_detection = choose_command(manifests, "lint_command")

                  write_json(
                      "commit_metadata.json",
                      "success",
                      {
                          "head_commit": head_sha,
                          "commits": commits,
                      },
                  )
                  write_json(
                      "file_creation_timeline.json",
                      "success",
                      {
                          "files": creation_events,
                          "best_effort": True,
                      },
                  )
                  write_json(
                      "repo_tree_summary.json",
                      "success",
                      {
                          "files": tree_files,
                          "directories": sorted(dir_counts.items()),
                          "extension_counts": sorted(extension_counts.items()),
                          "file_count": len(tree_files),
                      },
                  )
                  write_json(
                      "dependency_manifests.json",
                      "success" if manifests else "not_detected",
                      {
                          "detected": bool(manifests),
                          "manifests": manifests,
                      },
                  )
                  write_json("test_detection.json", "success" if test_detection["detected"] else "not_detected", test_detection)
                  test_results = run_command(test_detection["command"])
                  write_json("test_results.json", test_results["status"], test_results)
                  write_json("lint_detection.json", "success" if lint_detection["detected"] else "not_detected", lint_detection)
                  lint_results = run_command(lint_detection["command"])
                  write_json("lint_results.json", lint_results["status"], lint_results)
                  write_json(
                      "evidence_manifest.json",
                      "success",
                      {
                          "artifacts": written,
                          "generated_artifacts": [item["name"] for item in written],
                          "best_effort": True,
                      },
                  )
                  PY

              - name: Upload commit metadata
                if: always()
                uses: actions/upload-artifact@v4
                with:
                  name: winoe-commit-metadata
                  path: artifacts/commit_metadata.json
                  retention-days: 90
                  if-no-files-found: ignore

              - name: Upload file creation timeline
                if: always()
                uses: actions/upload-artifact@v4
                with:
                  name: winoe-file-creation-timeline
                  path: artifacts/file_creation_timeline.json
                  retention-days: 90
                  if-no-files-found: ignore

              - name: Upload repository tree summary
                if: always()
                uses: actions/upload-artifact@v4
                with:
                  name: winoe-repo-tree-summary
                  path: artifacts/repo_tree_summary.json
                  retention-days: 90
                  if-no-files-found: ignore

              - name: Upload dependency manifests
                if: always()
                uses: actions/upload-artifact@v4
                with:
                  name: winoe-dependency-manifests
                  path: artifacts/dependency_manifests.json
                  retention-days: 90
                  if-no-files-found: ignore

              - name: Upload test detection
                if: always()
                uses: actions/upload-artifact@v4
                with:
                  name: winoe-test-detection
                  path: artifacts/test_detection.json
                  retention-days: 90
                  if-no-files-found: ignore

              - name: Upload test results
                if: always()
                uses: actions/upload-artifact@v4
                with:
                  name: winoe-test-results
                  path: artifacts/test_results.json
                  retention-days: 90
                  if-no-files-found: ignore

              - name: Upload lint detection
                if: always()
                uses: actions/upload-artifact@v4
                with:
                  name: winoe-lint-detection
                  path: artifacts/lint_detection.json
                  retention-days: 90
                  if-no-files-found: ignore

              - name: Upload lint results
                if: always()
                uses: actions/upload-artifact@v4
                with:
                  name: winoe-lint-results
                  path: artifacts/lint_results.json
                  retention-days: 90
                  if-no-files-found: ignore

              - name: Upload evidence manifest
                if: always()
                uses: actions/upload-artifact@v4
                with:
                  name: winoe-evidence-manifest
                  path: artifacts/evidence_manifest.json
                  retention-days: 90
                  if-no-files-found: ignore
        """
        ).strip()
        + "\n"
    )


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
            "path": "README.md",
            "content": _project_brief_readme(
                trial=trial, scenario_version=scenario_version, task=task
            ),
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
            "path": _EVIDENCE_WORKFLOW_PATH,
            "content": build_evidence_capture_workflow_yaml(),
            "mode": "100644",
            "type": "blob",
        },
    ]


def _bootstrap_paths() -> list[str]:
    return [
        ".devcontainer/devcontainer.json",
        "README.md",
        ".gitignore",
        _EVIDENCE_WORKFLOW_PATH,
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


def _codespace_degradation_reason(exc: GithubError) -> str | None:
    """Return the explicit repo-only fallback reason for codespace creation.

    Only a GitHub service-unavailable response is allowed to degrade to a
    repo-only invite flow. A 404 is still retried first, then converted to the
    same repo-only fallback if GitHub never makes the repository visible.
    """
    if exc.status_code == 503:
        return "github_codespace_service_unavailable"
    return None


def _should_retry_codespace_error(exc: GithubError) -> bool:
    """Return whether a codespace error is transient enough to retry."""
    return exc.status_code == 404


async def _create_candidate_repo(
    *, github_client: GithubClient, owner: str, repo_name: str, default_branch: str
) -> dict[str, Any]:
    """Create the repo using the empty-repo API."""
    create_empty_repo = getattr(github_client, "create_empty_repo", None)
    if callable(create_empty_repo):
        return await create_empty_repo(
            owner=owner,
            repo_name=repo_name,
            private=True,
            default_branch=default_branch,
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
    repo = await ensure_repo_is_active(github_client, repo_full_name) or repo
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
        fallback_reason: str | None = None
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
                fallback_reason = _codespace_degradation_reason(exc)
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
                if fallback_reason is not None:
                    logger.warning(
                        "github_codespace_provision_degraded",
                        extra={
                            "trial_id": trial_id,
                            "candidate_session_id": candidate_session_id,
                            "repo_full_name": repo_full_name,
                            "status_code": exc.status_code,
                            "fallback_reason": fallback_reason,
                            "fallback_mode": "repo_only",
                            "safe_fallback": True,
                            "error_message": str(exc),
                            "elapsed_ms": _elapsed_ms(overall_started_at),
                        },
                    )
                    break
                if _should_retry_codespace_error(exc) and attempt < 6:
                    # GitHub can briefly lag while a new repo settles, so we
                    # retry the not-found case without degrading the flow.
                    logger.warning(
                        "github_codespace_provision_retrying",
                        extra={
                            "trial_id": trial_id,
                            "candidate_session_id": candidate_session_id,
                            "repo_full_name": repo_full_name,
                            "status_code": exc.status_code,
                            "retry_reason": "repo_not_ready_yet",
                            "retryable": True,
                            "attempt": attempt + 1,
                            "elapsed_ms": _elapsed_ms(overall_started_at),
                        },
                    )
                    await asyncio.sleep(_CODESPACE_RETRY_DELAY_SECONDS)
                    continue
                if exc.status_code == 404:
                    break
                logger.error(
                    "github_codespace_provision_failed",
                    extra={
                        "trial_id": trial_id,
                        "candidate_session_id": candidate_session_id,
                        "repo_full_name": repo_full_name,
                        "status_code": exc.status_code,
                        "failure_class": "hard_failure",
                        "retryable": False,
                        "error_message": str(exc),
                        "attempt": attempt + 1,
                    },
                )
                raise
        if codespace is None:
            assert last_codespace_error is not None
            fallback_reason = _codespace_degradation_reason(last_codespace_error)
            if fallback_reason is None and last_codespace_error.status_code == 404:
                fallback_reason = "github_codespace_service_unavailable"
            if fallback_reason is not None:
                logger.warning(
                    "github_codespace_provision_degraded",
                    extra={
                        "trial_id": trial_id,
                        "candidate_session_id": candidate_session_id,
                        "repo_full_name": repo_full_name,
                        "status_code": getattr(
                            last_codespace_error, "status_code", None
                        ),
                        "fallback_reason": fallback_reason,
                        "fallback_mode": "repo_only",
                        "safe_fallback": True,
                        "error_message": str(last_codespace_error),
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
        raise


__all__ = [
    "BootstrapRepoResult",
    "build_candidate_repo_name",
    "build_evidence_capture_workflow_yaml",
    "bootstrap_empty_candidate_repo",
]
