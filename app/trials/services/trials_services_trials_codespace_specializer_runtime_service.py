"""Runtime helpers for codespace specialization bundle generation."""

from __future__ import annotations

import asyncio
import difflib
import fnmatch
import json
import logging
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from app.ai import (
    CodespaceSpec,
    build_required_snapshot_prompt,
    require_agent_policy_snapshot,
    require_agent_runtime,
)
from app.integrations.codespace_specializer import (
    CodespaceSpecializerProviderError,
    CodespaceSpecializerRequest,
    get_codespace_specializer_provider,
)

logger = logging.getLogger(__name__)

_MAX_SNAPSHOT_FILES = 40
_MAX_SNAPSHOT_CHARS = 120_000
_MAX_FILE_SNAPSHOT_CHARS = 12_000
_MAX_OUTPUT_CHARS = 8_000
_RETRYABLE_CODESPACE_SPECIALIZER_ERROR_MARKERS = (
    "openai_request_failed:ratelimiterror",
    "openai_request_failed:apitimeouterror",
    "openai_request_failed:apiconnectionerror",
    "openai_request_failed:internalservererror",
    "openai_request_failed:serviceunavailableerror",
    "openai_request_failed:overloadederror",
    "rate limit",
    "too many requests",
    "429",
)
_HUNK_HEADER_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?P<section>.*)$"
)


class CodespaceSpecializerRuntimeError(RuntimeError):
    """Raised when bundle generation fails."""


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Represent local command execution output."""

    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True)
class CodespaceBundleArtifact:
    """Represent the bundle artifact persisted for one scenario version."""

    patch_payload_json: str
    commit_message: str
    base_template_sha: str | None
    model_name: str
    model_version: str
    prompt_version: str
    test_summary_json: dict
    provenance_json: dict


class _CodexPatchParseError(ValueError):
    """Raised when a Codex apply_patch block cannot be normalized."""


@dataclass(frozen=True, slots=True)
class _CodexPatchBlock:
    action: str
    path: str
    move_to: str | None = None
    body_lines: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _CodexPatchHunk:
    header: str
    lines: tuple[str, ...]


def resolve_codespace_spec(scenario_version) -> CodespaceSpec:
    """Return a validated codespace spec with a backwards-compatible fallback."""
    raw_spec = getattr(scenario_version, "codespace_spec_json", None) or {}
    if raw_spec:
        return CodespaceSpec.model_validate(raw_spec)
    storyline = (getattr(scenario_version, "storyline_md", "") or "").strip()
    summary = storyline.splitlines()[0].strip("# ").strip() or "Trial baseline"
    return CodespaceSpec(
        summary=summary,
        candidate_goal="Implement the scenario's shared Day 2/3 coding workspace.",
        acceptance_criteria=["Repository baseline matches the approved scenario."],
    )


def _build_context_only_bundle_artifact(
    *,
    scenario_version,
    template_repo_full_name: str,
    mode: str,
    model_name: str,
    model_version: str,
    fallback_reason: str | None = None,
) -> CodespaceBundleArtifact:
    """Build a deterministic context-only bundle artifact."""
    spec = resolve_codespace_spec(scenario_version)
    codespace_snapshot = require_agent_policy_snapshot(
        getattr(scenario_version, "ai_policy_snapshot_json", None),
        "codespace",
        scenario_version_id=getattr(scenario_version, "id", None),
    )
    patch_payload_json = json.dumps(
        {
            "files": [
                {
                    "path": "WINOE_TRIAL_CONTEXT.md",
                    "content": _build_demo_context_markdown(
                        spec, template_repo_full_name
                    ),
                    "executable": False,
                }
            ]
        },
        indent=2,
        sort_keys=True,
    )
    provenance_json = {
        "mode": mode,
        "templateRepoFullName": template_repo_full_name,
        "planMd": (
            "Create a single repository context file so candidate workspaces start with "
            "trial-specific instructions without mutating product code."
        ),
        "unifiedDiff": None,
    }
    if fallback_reason:
        provenance_json["fallbackReason"] = _truncate_text(
            fallback_reason,
            limit=_MAX_OUTPUT_CHARS,
        )
    return CodespaceBundleArtifact(
        patch_payload_json=patch_payload_json,
        commit_message="chore: prepare trial baseline",
        base_template_sha=None,
        model_name=model_name,
        model_version=model_version,
        prompt_version=str(codespace_snapshot["promptVersion"]),
        test_summary_json={
            "status": "skipped",
            "command": None,
            "attempts": [{"attempt": 1, "status": "skipped", "reason": mode}],
        },
        provenance_json=provenance_json,
    )


def build_demo_bundle_artifact(
    *,
    scenario_version,
    template_repo_full_name: str,
) -> CodespaceBundleArtifact:
    """Build a deterministic bundle artifact for demo or test runtime modes."""
    return _build_context_only_bundle_artifact(
        scenario_version=scenario_version,
        template_repo_full_name=template_repo_full_name,
        mode="demo_or_test",
        model_name="deterministic-demo",
        model_version="deterministic-demo",
    )


def build_retryable_provider_fallback_bundle_artifact(
    *,
    scenario_version,
    template_repo_full_name: str,
    fallback_reason: str,
) -> CodespaceBundleArtifact:
    """Build a deterministic bundle when the provider is transiently unavailable."""
    return _build_context_only_bundle_artifact(
        scenario_version=scenario_version,
        template_repo_full_name=template_repo_full_name,
        mode="provider_retryable_fallback",
        model_name="deterministic-provider-fallback",
        model_version="deterministic-provider-fallback",
        fallback_reason=fallback_reason,
    )


def is_retryable_codespace_specializer_error(exc: Exception) -> bool:
    """Return whether a specialization failure should degrade to a safe fallback."""
    message = str(exc).strip().lower()
    if not message:
        return False
    return any(
        marker in message for marker in _RETRYABLE_CODESPACE_SPECIALIZER_ERROR_MARKERS
    )


async def generate_codespace_bundle_artifact(
    *,
    template_repo_full_name: str,
    scenario_version,
    trial,
) -> CodespaceBundleArtifact:
    """Generate a provider-backed bundle artifact for a locked scenario version."""
    runtime = require_agent_runtime(
        getattr(scenario_version, "ai_policy_snapshot_json", None),
        "codespace",
        scenario_version_id=getattr(scenario_version, "id", None),
    )
    codespace_snapshot = require_agent_policy_snapshot(
        getattr(scenario_version, "ai_policy_snapshot_json", None),
        "codespace",
        scenario_version_id=getattr(scenario_version, "id", None),
    )
    prompt_version = (
        str(codespace_snapshot.get("promptVersion"))
        if isinstance(codespace_snapshot, dict)
        and isinstance(codespace_snapshot.get("promptVersion"), str)
        else ""
    )
    spec = resolve_codespace_spec(scenario_version)
    template_clone_url = _build_clone_url(template_repo_full_name)
    timeout_seconds = int(runtime.get("timeoutSeconds", 0) or 0) or 300

    with tempfile.TemporaryDirectory(prefix="winoe-codespace-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        repo_dir = temp_dir / "repo"
        await _clone_repo(
            repo_dir=repo_dir,
            clone_url=template_clone_url,
            timeout_seconds=timeout_seconds,
        )
        base_template_sha = await _git_head_sha(repo_dir)
        repo_snapshot = await _build_repo_snapshot(repo_dir, spec)
        run_context_md = _build_run_context(
            trial=trial,
            scenario_version=scenario_version,
            template_repo_full_name=template_repo_full_name,
            base_template_sha=base_template_sha,
        )
        system_prompt, rubric_prompt = build_required_snapshot_prompt(
            snapshot_json=getattr(scenario_version, "ai_policy_snapshot_json", None),
            agent_key="codespace",
            run_context_md=run_context_md,
            scenario_version_id=getattr(scenario_version, "id", None),
        )
        provider = get_codespace_specializer_provider(str(runtime["provider"]))
        request_model = str(runtime["model"])
        prompt_payload = {
            "trial": {
                "id": getattr(trial, "id", None),
                "title": getattr(trial, "title", None),
                "role": getattr(trial, "role", None),
                "techStack": getattr(trial, "tech_stack", None),
                "focus": getattr(trial, "focus", None),
                "companyContext": getattr(trial, "company_context", None),
            },
            "scenarioVersion": {
                "id": getattr(scenario_version, "id", None),
                "versionIndex": getattr(scenario_version, "version_index", None),
                "templateKey": getattr(scenario_version, "template_key", None),
                "storylineMd": getattr(scenario_version, "storyline_md", None),
            },
            "codespaceSpec": spec.model_dump(),
            "rubricGuidance": rubric_prompt,
        }

        previous_failure: dict | None = None
        repair_repo_snapshot: dict | None = None
        attempts: list[dict] = []
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            active_repo_snapshot = repair_repo_snapshot or repo_snapshot
            user_prompt_payload = {
                **prompt_payload,
                "repositorySnapshot": active_repo_snapshot,
                "attempt": attempt,
                "repairContext": previous_failure,
            }
            if repair_repo_snapshot is not None:
                user_prompt_payload["baseRepositorySnapshot"] = repo_snapshot
                user_prompt_payload["repairRepositorySnapshot"] = repair_repo_snapshot
            user_prompt = json.dumps(
                user_prompt_payload,
                indent=2,
                sort_keys=True,
            )
            try:
                proposal = provider.specialize_codespace(
                    request=CodespaceSpecializerRequest(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model=request_model,
                    )
                )
            except CodespaceSpecializerProviderError as exc:
                raise CodespaceSpecializerRuntimeError(str(exc)) from exc

            await _reset_repo(repo_dir)
            apply_result = await _apply_unified_diff(
                repo_dir=repo_dir,
                unified_diff=proposal.result.unified_diff,
            )
            if apply_result.exit_code != 0:
                previous_failure = {
                    "failureType": "apply_error",
                    "stdout": _truncate_text(apply_result.stdout),
                    "stderr": _truncate_text(apply_result.stderr),
                    "previousPlanMd": proposal.result.plan_md,
                    "previousCommitMessage": proposal.result.commit_message,
                    "previousUnifiedDiff": _truncate_text(
                        proposal.result.unified_diff,
                        limit=200_000,
                    ),
                }
                repair_repo_snapshot = None
                attempts.append(
                    {
                        "attempt": attempt,
                        "status": "apply_failed",
                        "stdout": _truncate_text(apply_result.stdout),
                        "stderr": _truncate_text(apply_result.stderr),
                    }
                )
                if attempt < max_attempts:
                    continue
                raise CodespaceSpecializerRuntimeError("codespace_patch_apply_failed")

            test_command = _resolve_test_command(repo_dir, spec)
            if test_command is None:
                patch_payload_json = await _build_patch_payload_json(repo_dir)
                return CodespaceBundleArtifact(
                    patch_payload_json=patch_payload_json,
                    commit_message=proposal.result.commit_message,
                    base_template_sha=base_template_sha,
                    model_name=proposal.model_name,
                    model_version=proposal.model_version,
                    prompt_version=prompt_version,
                    test_summary_json={
                        "status": "skipped",
                        "command": None,
                        "attempts": [
                            *attempts,
                            {
                                "attempt": attempt,
                                "status": "skipped",
                                "reason": "missing_test_command",
                            },
                        ],
                    },
                    provenance_json={
                        "templateRepoFullName": template_repo_full_name,
                        "planMd": proposal.result.plan_md,
                        "unifiedDiff": _truncate_text(
                            proposal.result.unified_diff,
                            limit=200_000,
                        ),
                        "attemptCount": attempt,
                        "repoSnapshot": repo_snapshot,
                    },
                )

            test_result = await _run_shell_command(
                command=test_command,
                cwd=repo_dir,
                timeout_seconds=timeout_seconds,
            )
            attempts.append(
                {
                    "attempt": attempt,
                    "status": "passed" if test_result.exit_code == 0 else "failed",
                    "command": test_command,
                    "exitCode": test_result.exit_code,
                    "stdout": _truncate_text(test_result.stdout),
                    "stderr": _truncate_text(test_result.stderr),
                }
            )
            if test_result.exit_code == 0:
                patch_payload_json = await _build_patch_payload_json(repo_dir)
                return CodespaceBundleArtifact(
                    patch_payload_json=patch_payload_json,
                    commit_message=proposal.result.commit_message,
                    base_template_sha=base_template_sha,
                    model_name=proposal.model_name,
                    model_version=proposal.model_version,
                    prompt_version=prompt_version,
                    test_summary_json={
                        "status": "passed",
                        "command": test_command,
                        "attempts": attempts,
                    },
                    provenance_json={
                        "templateRepoFullName": template_repo_full_name,
                        "planMd": proposal.result.plan_md,
                        "unifiedDiff": _truncate_text(
                            proposal.result.unified_diff,
                            limit=200_000,
                        ),
                        "attemptCount": attempt,
                        "repoSnapshot": repo_snapshot,
                    },
                )

            previous_failure = {
                "failureType": "test_failure",
                "command": test_command,
                "stdout": _truncate_text(test_result.stdout),
                "stderr": _truncate_text(test_result.stderr),
                "exitCode": test_result.exit_code,
                "previousPlanMd": proposal.result.plan_md,
                "previousCommitMessage": proposal.result.commit_message,
                "previousUnifiedDiff": _truncate_text(
                    proposal.result.unified_diff,
                    limit=200_000,
                ),
            }
            repair_repo_snapshot = await _build_repo_snapshot(
                repo_dir,
                spec,
                priority_paths=await _list_changed_paths(repo_dir),
            )

        error_detail = previous_failure or {"failureType": "unknown"}
        raise CodespaceSpecializerRuntimeError(
            f"codespace_tests_failed:{json.dumps(error_detail, sort_keys=True)}"
        )


def _build_demo_context_markdown(
    spec: CodespaceSpec,
    template_repo_full_name: str,
) -> str:
    lines = [
        "# Winoe Trial Context",
        "",
        f"Template repo: `{template_repo_full_name}`",
        "",
        f"Summary: {spec.summary}",
        "",
        f"Candidate goal: {spec.candidate_goal}",
        "",
        "Acceptance criteria:",
    ]
    lines.extend(f"- {criterion}" for criterion in spec.acceptance_criteria)
    if spec.test_focus:
        lines.extend(["", "Testing focus:"])
        lines.extend(f"- {item}" for item in spec.test_focus)
    return "\n".join(lines).strip() + "\n"


def _build_run_context(
    *,
    trial,
    scenario_version,
    template_repo_full_name: str,
    base_template_sha: str | None,
) -> str:
    return (
        f"Trial ID: {getattr(trial, 'id', None)}\n"
        f"Scenario version ID: {getattr(scenario_version, 'id', None)}\n"
        f"Template key: {getattr(scenario_version, 'template_key', None)}\n"
        f"Template repo: {template_repo_full_name}\n"
        f"Base template SHA: {base_template_sha or 'unknown'}"
    )


def _build_clone_url(repo_full_name: str) -> str:
    token = (os.environ.get("WINOE_GITHUB_TOKEN") or "").strip()
    if not token:
        from app.config import settings

        token = (settings.github.GITHUB_TOKEN or "").strip()
    if token:
        return (
            f"https://x-access-token:{quote(token, safe='')}@github.com/"
            f"{repo_full_name}.git"
        )
    return f"https://github.com/{repo_full_name}.git"


async def _clone_repo(
    *,
    repo_dir: Path,
    clone_url: str,
    timeout_seconds: int,
) -> None:
    result = await _run_exec(
        ["git", "clone", "--depth", "1", clone_url, str(repo_dir)],
        cwd=repo_dir.parent,
        timeout_seconds=timeout_seconds,
    )
    if result.exit_code != 0:
        raise CodespaceSpecializerRuntimeError(
            f"codespace_clone_failed:{_truncate_text(result.stderr)}"
        )


async def _git_head_sha(repo_dir: Path) -> str | None:
    result = await _run_exec(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_dir,
        timeout_seconds=30,
    )
    if result.exit_code != 0:
        return None
    return result.stdout.strip() or None


async def _build_repo_snapshot(
    repo_dir: Path,
    spec: CodespaceSpec,
    priority_paths: list[str] | None = None,
) -> dict:
    tracked_result = await _run_exec(
        ["git", "ls-files"],
        cwd=repo_dir,
        timeout_seconds=30,
    )
    if tracked_result.exit_code != 0:
        raise CodespaceSpecializerRuntimeError("codespace_ls_files_failed")
    untracked_result = await _run_exec(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo_dir,
        timeout_seconds=30,
    )
    if untracked_result.exit_code != 0:
        raise CodespaceSpecializerRuntimeError("codespace_ls_untracked_failed")
    tracked_files = [
        line.strip()
        for line in tracked_result.stdout.splitlines()
        if line.strip() and not _is_skipped_repo_path(line.strip())
    ]
    untracked_files = [
        line.strip()
        for line in untracked_result.stdout.splitlines()
        if line.strip() and not _is_skipped_repo_path(line.strip())
    ]
    repo_paths = list(dict.fromkeys([*tracked_files, *untracked_files]))
    prioritized = _prioritize_paths(
        repo_paths,
        spec,
        priority_paths=priority_paths,
    )
    file_payloads: list[dict[str, str]] = []
    consumed_chars = 0
    for relative_path in prioritized:
        if len(file_payloads) >= _MAX_SNAPSHOT_FILES:
            break
        abs_path = repo_dir / relative_path
        if not abs_path.is_file():
            continue
        try:
            content = abs_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        content = content[:_MAX_FILE_SNAPSHOT_CHARS]
        next_chars = consumed_chars + len(content)
        if next_chars > _MAX_SNAPSHOT_CHARS:
            break
        consumed_chars = next_chars
        file_payloads.append({"path": relative_path, "content": content})
    return {
        "trackedPaths": tracked_files[:200],
        "untrackedPaths": untracked_files[:200],
        "files": file_payloads,
        "truncated": len(file_payloads) < len(repo_paths),
    }


def _prioritize_paths(
    tracked_files: list[str],
    spec: CodespaceSpec,
    priority_paths: list[str] | None = None,
) -> list[str]:
    base_priority = [
        "README.md",
        "package.json",
        "pnpm-lock.yaml",
        "package-lock.json",
        "yarn.lock",
        "pyproject.toml",
        "pytest.ini",
        "requirements.txt",
        "Cargo.toml",
        "go.mod",
        ".github/workflows",
    ]
    wanted = list(
        dict.fromkeys([*(priority_paths or []), *spec.target_files, *base_priority])
    )
    priority_patterns = tuple(
        (index, pattern.strip())
        for index, pattern in enumerate(wanted)
        if pattern and pattern.strip()
    )
    return sorted(
        tracked_files,
        key=lambda path: (
            *_priority_key_for_path(path, priority_patterns),
            path,
        ),
    )


def _priority_key_for_path(
    path: str,
    priority_patterns: tuple[tuple[int, str], ...],
) -> tuple[int, int]:
    for index, pattern in priority_patterns:
        if _path_matches_priority_pattern(path, pattern):
            has_glob = any(token in pattern for token in "*?[")
            return (1 if has_glob else 0, index)
    return (2, len(priority_patterns) + 1)


def _path_matches_priority_pattern(path: str, pattern: str) -> bool:
    normalized_pattern = pattern.strip().rstrip("/")
    if not normalized_pattern:
        return False
    if path == normalized_pattern:
        return True
    if fnmatch.fnmatch(path, normalized_pattern):
        return True
    if path.startswith(normalized_pattern + "/"):
        return True
    pattern_path = Path(normalized_pattern)
    if pattern_path.suffix:
        stem_prefix = str(pattern_path.with_suffix(""))
        if stem_prefix and path.startswith(stem_prefix + "/"):
            return True
    return False


async def _list_changed_paths(repo_dir: Path) -> list[str]:
    result = await _run_exec(
        ["git", "status", "--short"],
        cwd=repo_dir,
        timeout_seconds=30,
    )
    if result.exit_code != 0:
        return []
    changed_paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path_text = line[3:].strip() if len(line) > 3 else ""
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        if not path_text or _is_skipped_repo_path(path_text):
            continue
        changed_paths.append(path_text)
    return list(dict.fromkeys(changed_paths))


def _is_skipped_repo_path(path: str) -> bool:
    parts = path.split("/")
    return any(
        part in {"node_modules", "dist", "build", "coverage", ".next", ".git"}
        for part in parts
    )


def _normalize_specializer_patch(
    *,
    repo_dir: Path,
    patch_text: str,
) -> tuple[str, str | None]:
    if not _looks_like_codex_patch(patch_text):
        return patch_text, None
    try:
        normalized = _convert_codex_patch_to_unified_diff(
            repo_dir=repo_dir,
            patch_text=patch_text,
        )
    except _CodexPatchParseError as exc:
        return patch_text, f"codespace_codex_patch_parse_failed:{exc}"
    if not normalized.strip():
        return patch_text, "codespace_codex_patch_empty_after_conversion"
    return normalized, None


def _looks_like_codex_patch(patch_text: str) -> bool:
    return patch_text.lstrip().startswith("*** Begin Patch")


def _convert_codex_patch_to_unified_diff(*, repo_dir: Path, patch_text: str) -> str:
    blocks = _parse_codex_patch_blocks(patch_text)
    original_contents: dict[str, str | None] = {}
    current_contents: dict[str, str | None] = {}
    affected_paths: set[str] = set()

    def _get_content(path: str) -> str | None:
        if path not in current_contents:
            content = _load_repo_text_or_none(repo_dir, path)
            original_contents[path] = content
            current_contents[path] = content
        return current_contents[path]

    def _set_content(path: str, content: str | None) -> None:
        if path not in original_contents:
            original_contents[path] = _load_repo_text_or_none(repo_dir, path)
        current_contents[path] = content
        affected_paths.add(path)

    for block in blocks:
        if block.action == "delete":
            _get_content(block.path)
            _set_content(block.path, None)
            continue
        if block.action == "add":
            _get_content(block.path)
            _set_content(
                block.path,
                _render_codex_add_file_content(block.body_lines),
            )
            continue
        if block.action != "update":
            raise _CodexPatchParseError(f"Unsupported patch action: {block.action}")

        source_text = _get_content(block.path)
        if source_text is None:
            raise _CodexPatchParseError(f"Update target does not exist: {block.path}")
        target_text = _apply_codex_update_hunks(
            source_text=source_text,
            path=block.path,
            hunks=_parse_codex_update_hunks(block.path, block.body_lines),
        )
        if block.move_to and block.move_to != block.path:
            _set_content(block.path, None)
            _get_content(block.move_to)
            _set_content(block.move_to, target_text)
            continue
        _set_content(block.path, target_text)

    diff_blocks: list[str] = []
    for path in sorted(affected_paths):
        original_text = original_contents.get(path)
        current_text = current_contents.get(path)
        if current_text == original_text:
            continue
        block = _render_unified_diff_block(
            source_text=original_text or "",
            target_text=current_text or "",
            old_path=path if original_text is not None else None,
            new_path=path if current_text is not None else None,
            target_path=path,
        )
        if block is not None:
            diff_blocks.append(block)
    return "\n".join(diff_blocks).rstrip() + ("\n" if diff_blocks else "")


def _parse_codex_patch_blocks(patch_text: str) -> list[_CodexPatchBlock]:
    lines = patch_text.splitlines()
    blocks: list[_CodexPatchBlock] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line != "*** Begin Patch":
            raise _CodexPatchParseError(f"Unexpected patch line: {line}")
        index += 1
        if index >= len(lines):
            raise _CodexPatchParseError("Patch block ended before file directive.")
        directive = lines[index]
        index += 1
        action: str
        path: str
        move_to: str | None = None
        if directive.startswith("*** Add File: "):
            action = "add"
            path = directive.removeprefix("*** Add File: ").strip()
        elif directive.startswith("*** Delete File: "):
            action = "delete"
            path = directive.removeprefix("*** Delete File: ").strip()
        elif directive.startswith("*** Update File: "):
            action = "update"
            path = directive.removeprefix("*** Update File: ").strip()
            if index < len(lines) and lines[index].startswith("*** Move to: "):
                move_to = lines[index].removeprefix("*** Move to: ").strip()
                index += 1
        else:
            raise _CodexPatchParseError(f"Unsupported patch directive: {directive}")
        if not path:
            raise _CodexPatchParseError("Patch directive is missing a file path.")

        body_lines: list[str] = []
        while index < len(lines) and lines[index] != "*** End Patch":
            body_lines.append(lines[index])
            index += 1
        if index >= len(lines):
            raise _CodexPatchParseError(
                f"Patch block for {path} is missing an end marker."
            )
        index += 1
        blocks.append(
            _CodexPatchBlock(
                action=action,
                path=path,
                move_to=move_to,
                body_lines=tuple(body_lines),
            )
        )
    return blocks


def _load_repo_text_or_none(repo_dir: Path, relative_path: str) -> str | None:
    target = repo_dir / relative_path
    if not target.exists():
        return None
    return target.read_text(encoding="utf-8")


def _render_codex_add_file_content(body_lines: tuple[str, ...]) -> str:
    content_lines: list[str] = []
    for line in body_lines:
        if line == "*** End of File":
            continue
        content_lines.append(line[1:] if line.startswith("+") else line)
    if not content_lines:
        return ""
    return "\n".join(content_lines) + "\n"


def _parse_codex_update_hunks(
    path: str,
    body_lines: tuple[str, ...],
) -> list[_CodexPatchHunk]:
    hunks: list[_CodexPatchHunk] = []
    current_header = ""
    current_lines: list[str] = []
    for line in body_lines:
        if line == "*** End of File":
            continue
        if line.startswith("@@"):
            if current_lines or current_header:
                hunks.append(
                    _CodexPatchHunk(
                        header=current_header,
                        lines=tuple(current_lines),
                    )
                )
            current_header = line[2:].strip()
            current_lines = []
            continue
        current_lines.append(line)

    if current_lines or current_header:
        hunks.append(
            _CodexPatchHunk(
                header=current_header,
                lines=tuple(current_lines),
            )
        )
    if not hunks and body_lines:
        raise _CodexPatchParseError(
            f"Update File block for {path} did not contain any hunk content."
        )
    return hunks


def _apply_codex_update_hunks(
    *,
    source_text: str,
    path: str,
    hunks: list[_CodexPatchHunk],
) -> str:
    if not hunks:
        return source_text

    target_lines = source_text.splitlines()
    cursor = 0
    for hunk in hunks:
        normalized_lines = tuple(
            _normalize_codex_hunk_line(line) for line in hunk.lines
        )
        if any(line and line[:1] not in {" ", "+", "-"} for line in normalized_lines):
            raise _CodexPatchParseError(
                f"Update File block for {path} contains an invalid hunk line."
            )
        old_lines = [line[1:] for line in normalized_lines if line[:1] in {" ", "-"}]
        new_lines = [line[1:] for line in normalized_lines if line[:1] in {" ", "+"}]
        match_index = _find_hunk_match(
            source_lines=target_lines,
            old_lines=old_lines,
            expected_index=max(0, min(len(target_lines), cursor)),
        )
        if match_index is None:
            raise _CodexPatchParseError(
                f"Unable to match update hunk for {path}: {hunk.header or '@@'}"
            )
        target_lines[match_index : match_index + len(old_lines)] = new_lines
        cursor = match_index + len(new_lines)

    if not target_lines:
        return ""
    return "\n".join(target_lines) + "\n"


def _normalize_codex_hunk_line(line: str) -> str:
    """Treat bare blank lines as context lines in Codex Update File hunks."""
    if line == "":
        return " "
    return line


async def _apply_unified_diff(*, repo_dir: Path, unified_diff: str) -> CommandResult:
    patch_path = repo_dir / ".winoe_specializer.patch"
    patch_text = _strip_fence(unified_diff)
    patch_text, normalize_error = _normalize_specializer_patch(
        repo_dir=repo_dir,
        patch_text=patch_text,
    )
    if normalize_error is not None:
        return CommandResult(exit_code=1, stdout="", stderr=normalize_error)
    patch_path.write_text(patch_text, encoding="utf-8")
    try:
        result = await _run_exec(
            [
                "git",
                "apply",
                "--whitespace=nowarn",
                str(patch_path),
            ],
            cwd=repo_dir,
            timeout_seconds=60,
        )
        if result.exit_code == 0:
            return result
        candidate_patch = (
            _repair_unified_diff(
                repo_dir=repo_dir,
                patch_text=patch_text,
            )
            or patch_text
        )
        if candidate_patch != patch_text:
            patch_path.write_text(candidate_patch, encoding="utf-8")

        repaired_result = await _run_exec(
            [
                "git",
                "apply",
                "--recount",
                "--whitespace=nowarn",
                str(patch_path),
            ],
            cwd=repo_dir,
            timeout_seconds=60,
        )
        if repaired_result.exit_code == 0:
            return repaired_result

        canonical_patch = _rewrite_patch_as_full_file_diffs(
            repo_dir=repo_dir,
            patch_text=candidate_patch,
        )
        if not canonical_patch or canonical_patch == candidate_patch:
            return repaired_result
        patch_path.write_text(canonical_patch, encoding="utf-8")
        return await _run_exec(
            [
                "git",
                "apply",
                "--recount",
                "--whitespace=nowarn",
                str(patch_path),
            ],
            cwd=repo_dir,
            timeout_seconds=60,
        )
    finally:
        try:
            patch_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("codespace_specializer_patch_cleanup_failed")


async def _build_patch_payload_json(repo_dir: Path) -> str:
    result = await _run_exec(
        ["git", "diff", "--name-status", "--find-renames"],
        cwd=repo_dir,
        timeout_seconds=30,
    )
    if result.exit_code != 0:
        raise CodespaceSpecializerRuntimeError("codespace_diff_name_status_failed")
    entries: list[dict[str, object]] = []
    for line in result.stdout.splitlines():
        parts = [part for part in line.split("\t") if part]
        if not parts:
            continue
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            old_path = parts[1]
            new_path = parts[2]
            entries.append({"path": old_path, "delete": True})
            entries.append(await _build_content_entry(repo_dir, new_path))
            continue
        if len(parts) < 2:
            continue
        path = parts[1]
        if status.startswith("D"):
            entries.append({"path": path, "delete": True})
            continue
        entries.append(await _build_content_entry(repo_dir, path))
    if not entries:
        raise CodespaceSpecializerRuntimeError("codespace_specializer_empty_patch")
    return json.dumps({"files": entries}, indent=2, sort_keys=True)


async def _build_content_entry(repo_dir: Path, relative_path: str) -> dict[str, object]:
    abs_path = repo_dir / relative_path
    try:
        content = abs_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        raise CodespaceSpecializerRuntimeError(
            f"codespace_non_text_patch_file:{relative_path}"
        ) from exc
    executable = bool(abs_path.stat().st_mode & stat.S_IXUSR)
    return {
        "path": relative_path,
        "content": content,
        "executable": executable,
    }


def _resolve_test_command(repo_dir: Path, spec: CodespaceSpec) -> str | None:
    if spec.test_command:
        command = spec.test_command.strip() or None
        return _normalize_test_command(repo_dir, command) if command else None
    package_json_path = repo_dir / "package.json"
    if package_json_path.is_file():
        try:
            package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            package_json = {}
        scripts = package_json.get("scripts") if isinstance(package_json, dict) else {}
        if isinstance(scripts, dict) and isinstance(scripts.get("test"), str):
            if (repo_dir / "pnpm-lock.yaml").exists():
                return "pnpm test"
            if (repo_dir / "yarn.lock").exists():
                return "yarn test"
            return "npm test"
    if any((repo_dir / name).exists() for name in ("pyproject.toml", "pytest.ini")):
        return _normalize_test_command(repo_dir, "pytest")
    if (repo_dir / "go.mod").exists():
        return "go test ./..."
    if (repo_dir / "Cargo.toml").exists():
        return "cargo test"
    return None


def _normalize_test_command(repo_dir: Path, command: str) -> str:
    normalized = command.strip()
    if not normalized:
        return normalized
    if "PYTHONPATH=" in normalized:
        return normalized
    if normalized.startswith("pytest") and (repo_dir / "app").is_dir():
        return f"PYTHONPATH=. {normalized}"
    return normalized


def _repair_unified_diff(*, repo_dir: Path, patch_text: str) -> str | None:
    repaired = patch_text
    changed = False

    recounted = _rewrite_unified_diff_hunk_counts(repaired)
    if recounted is not None and recounted != repaired:
        repaired = recounted
        changed = True

    rewritten = _rewrite_malformed_full_file_diff(
        repo_dir=repo_dir, patch_text=repaired
    )
    if rewritten is not None and rewritten != repaired:
        repaired = rewritten
        changed = True

    if not changed:
        return None
    return repaired


def _rewrite_unified_diff_hunk_counts(patch_text: str) -> str | None:
    lines = patch_text.splitlines()
    if not lines:
        return None

    rewritten: list[str] = []
    changed = False
    index = 0
    while index < len(lines):
        line = lines[index]
        match = _HUNK_HEADER_RE.match(line)
        if match is None:
            rewritten.append(line)
            index += 1
            continue

        body_lines: list[str] = []
        index += 1
        while index < len(lines):
            current = lines[index]
            if current.startswith("@@ ") or current.startswith("diff --git "):
                break
            body_lines.append(current)
            index += 1

        old_count = sum(1 for body_line in body_lines if body_line[:1] in {" ", "-"})
        new_count = sum(1 for body_line in body_lines if body_line[:1] in {" ", "+"})
        old_count_text = f",{old_count}" if old_count != 1 else ""
        new_count_text = f",{new_count}" if new_count != 1 else ""
        header = (
            f"@@ -{match.group('old_start')}{old_count_text} "
            f"+{match.group('new_start')}{new_count_text} @@{match.group('section')}"
        )
        if header != line:
            changed = True
        rewritten.append(header)
        rewritten.extend(body_lines)

    if not changed:
        return None
    return "\n".join(rewritten).rstrip() + "\n"


def _rewrite_malformed_full_file_diff(*, repo_dir: Path, patch_text: str) -> str | None:
    blocks = _split_diff_blocks(patch_text)
    if not blocks:
        return None

    rewritten_blocks: list[str] = []
    changed = False
    for block in blocks:
        if "\n@@" in block or block.startswith("@@"):
            rewritten_blocks.append(block)
            continue
        repaired = _rewrite_full_file_block(
            repo_dir=repo_dir,
            block=block,
            allow_hunks=False,
        )
        if repaired is None:
            rewritten_blocks.append(block)
            continue
        rewritten_blocks.append(repaired)
        changed = True

    if not changed:
        return None
    return "\n".join(rewritten_blocks).rstrip() + "\n"


def _split_diff_blocks(patch_text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            if current:
                blocks.append("\n".join(current))
            current = [line]
            continue
        if current:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def _rewrite_patch_as_full_file_diffs(*, repo_dir: Path, patch_text: str) -> str | None:
    blocks = _split_diff_blocks(patch_text)
    if not blocks:
        return None

    rewritten_blocks: list[str] = []
    changed = False
    for block in blocks:
        repaired = _rewrite_block_against_source(repo_dir=repo_dir, block=block)
        if repaired is None:
            repaired = _rewrite_add_or_delete_block_as_full_file_diff(
                repo_dir=repo_dir,
                block=block,
            )
        if repaired is None:
            repaired = _rewrite_single_hunk_full_file_block(
                repo_dir=repo_dir,
                block=block,
            )
        if repaired is None:
            rewritten_blocks.append(block)
            continue
        rewritten_blocks.append(repaired)
        if repaired != block:
            changed = True

    if not changed:
        return None
    return "\n".join(rewritten_blocks).rstrip() + "\n"


def _rewrite_add_or_delete_block_as_full_file_diff(
    *,
    repo_dir: Path,
    block: str,
) -> str | None:
    if "--- /dev/null" not in block and "+++ /dev/null" not in block:
        return None
    return _rewrite_full_file_block(
        repo_dir=repo_dir,
        block=block,
        allow_hunks=True,
    )


def _rewrite_single_hunk_full_file_block(
    *,
    repo_dir: Path,
    block: str,
) -> str | None:
    lines = block.splitlines()
    hunk_headers = [line for line in lines if line.startswith("@@ ")]
    if len(hunk_headers) != 1:
        return None
    match = _HUNK_HEADER_RE.match(hunk_headers[0])
    if match is None:
        return None
    old_start = int(match.group("old_start"))
    if old_start != 1:
        return None
    old_count = int(match.group("old_count") or "1")

    diff_header = lines[0].split() if lines else []
    if len(diff_header) < 4:
        return None
    old_rel = diff_header[2][2:] if diff_header[2].startswith("a/") else diff_header[2]
    if not old_rel or old_rel == "/dev/null":
        return None

    source_file = repo_dir / old_rel
    if not source_file.exists():
        return None
    source_line_count = len(source_file.read_text(encoding="utf-8").splitlines())
    if old_count < source_line_count:
        return None

    return _rewrite_full_file_block(
        repo_dir=repo_dir,
        block=block,
        allow_hunks=True,
    )


def _rewrite_block_against_source(*, repo_dir: Path, block: str) -> str | None:
    if "\n@@" not in block and not block.startswith("@@"):
        return _rewrite_full_file_block(
            repo_dir=repo_dir,
            block=block,
            allow_hunks=False,
        )

    lines = block.splitlines()
    if not lines or not lines[0].startswith("diff --git "):
        return None
    diff_parts = lines[0].split()
    if len(diff_parts) < 4:
        return None

    old_rel = diff_parts[2][2:] if diff_parts[2].startswith("a/") else diff_parts[2]
    new_rel = diff_parts[3][2:] if diff_parts[3].startswith("b/") else diff_parts[3]

    old_header = None
    new_header = None
    seen_plus_plus = False
    hunks: list[tuple[int, list[str]]] = []
    current_hunk_old_start: int | None = None
    current_hunk_lines: list[str] = []

    for line in lines[1:]:
        if line.startswith("--- "):
            old_header = line[4:].strip()
            continue
        if line.startswith("+++ "):
            new_header = line[4:].strip()
            seen_plus_plus = True
            continue
        if not seen_plus_plus:
            continue
        if line.startswith("@@ "):
            if current_hunk_old_start is not None:
                hunks.append((current_hunk_old_start, current_hunk_lines))
            match = _HUNK_HEADER_RE.match(line)
            if match is None:
                return None
            current_hunk_old_start = int(match.group("old_start"))
            current_hunk_lines = []
            continue
        if line == r"\ No newline at end of file":
            continue
        if current_hunk_old_start is None:
            return None
        current_hunk_lines.append(line)

    if current_hunk_old_start is not None:
        hunks.append((current_hunk_old_start, current_hunk_lines))
    if not hunks:
        return None

    old_path = None if old_header == "/dev/null" else old_rel
    new_path = None if new_header == "/dev/null" else new_rel
    actual_existing_path = repo_dir / (new_rel or old_rel)
    if (
        old_path is None
        and actual_existing_path.exists()
        and _hunks_are_additions_only(hunks)
    ):
        return _rewrite_full_file_block(
            repo_dir=repo_dir,
            block=block,
            allow_hunks=True,
        )

    target_path = new_path or old_path or new_rel or old_rel
    if not target_path:
        return None

    source_text = ""
    source_path = old_path or (new_rel if actual_existing_path.exists() else None)
    if source_path:
        source_file = repo_dir / source_path
        if source_file.exists():
            source_text = source_file.read_text(encoding="utf-8")
            if old_path is None:
                old_path = source_path
    if new_path is None and old_path and not _hunks_are_deletions_only(hunks):
        new_path = old_path

    target_lines = source_text.splitlines()
    line_offset = 0
    for old_start, hunk_lines in hunks:
        if any(line and line[0] not in {" ", "+", "-"} for line in hunk_lines):
            return None
        old_lines = [line[1:] for line in hunk_lines if line[:1] in {" ", "-"}]
        new_lines = [line[1:] for line in hunk_lines if line[:1] in {" ", "+"}]
        expected_index = (
            0
            if old_start <= 0
            else max(0, min(len(target_lines), old_start - 1 + line_offset))
        )
        match_index = _find_hunk_match(
            source_lines=target_lines,
            old_lines=old_lines,
            expected_index=expected_index,
        )
        if match_index is None:
            return None
        target_lines[match_index : match_index + len(old_lines)] = new_lines
        line_offset += len(new_lines) - len(old_lines)

    target_text = "\n".join(target_lines)
    if target_lines:
        target_text += "\n"
    normalized_target_path = new_path or old_path or target_path
    return _render_unified_diff_block(
        source_text=source_text,
        target_text=target_text,
        old_path=old_path,
        new_path=new_path,
        target_path=normalized_target_path,
    )


def _hunks_are_additions_only(hunks: list[tuple[int, list[str]]]) -> bool:
    return all(
        all(line.startswith("+") for line in hunk_lines)
        for _old_start, hunk_lines in hunks
    )


def _hunks_are_deletions_only(hunks: list[tuple[int, list[str]]]) -> bool:
    return all(
        all(line.startswith("-") for line in hunk_lines)
        for _old_start, hunk_lines in hunks
    )


def _find_hunk_match(
    *,
    source_lines: list[str],
    old_lines: list[str],
    expected_index: int,
) -> int | None:
    if not old_lines:
        return max(0, min(len(source_lines), expected_index))

    max_start = len(source_lines) - len(old_lines)
    if max_start < 0:
        return None

    checked: set[int] = set()
    for offset in range(0, max_start + 1):
        candidates = [expected_index - offset, expected_index + offset]
        for candidate in candidates:
            if candidate < 0 or candidate > max_start or candidate in checked:
                continue
            checked.add(candidate)
            if source_lines[candidate : candidate + len(old_lines)] == old_lines:
                return candidate

    return None


def _rewrite_full_file_block(
    *,
    repo_dir: Path,
    block: str,
    allow_hunks: bool,
) -> str | None:
    lines = block.splitlines()
    if not lines or not lines[0].startswith("diff --git "):
        return None

    diff_parts = lines[0].split()
    if len(diff_parts) < 4:
        return None
    old_rel = diff_parts[2][2:] if diff_parts[2].startswith("a/") else diff_parts[2]
    new_rel = diff_parts[3][2:] if diff_parts[3].startswith("b/") else diff_parts[3]

    old_header = None
    new_header = None
    seen_plus_plus = False
    body_lines: list[str] = []
    for line in lines[1:]:
        if line.startswith("--- "):
            old_header = line[4:].strip()
            continue
        if line.startswith("+++ "):
            new_header = line[4:].strip()
            seen_plus_plus = True
            continue
        if not seen_plus_plus:
            continue
        if line.startswith("@@ "):
            if not allow_hunks:
                return None
            continue
        if line == r"\ No newline at end of file":
            continue
        body_lines.append(line)
    if not body_lines:
        return None

    old_path = None if old_header == "/dev/null" else old_rel
    new_path = None if new_header == "/dev/null" else new_rel
    actual_existing_path = repo_dir / (new_rel or old_rel)
    if old_path is None and actual_existing_path.exists():
        old_path = new_rel or old_rel
    if (
        new_path is None
        and old_path
        and any(line[:1] in {" ", "+"} for line in body_lines)
    ):
        new_path = old_path
    target_path = new_path or old_path
    if not target_path:
        return None

    normalized_body_lines = _coerce_full_file_body_lines(
        body_lines,
        old_path=old_path,
        new_path=new_path,
    )
    if normalized_body_lines is None:
        return None

    source_text = ""
    if old_path:
        source_file = repo_dir / old_path
        if source_file.exists():
            source_text = source_file.read_text(encoding="utf-8")

    target_lines: list[str] = []
    for line in normalized_body_lines:
        if line.startswith("-"):
            continue
        if line.startswith(("+", " ")):
            target_lines.append(line[1:])
            continue
        target_lines.append(line)
    target_text = "\n".join(target_lines)
    if target_lines:
        target_text += "\n"

    return _render_unified_diff_block(
        source_text=source_text,
        target_text=target_text,
        old_path=old_path,
        new_path=new_path,
        target_path=target_path,
    )


def _coerce_full_file_body_lines(
    body_lines: list[str],
    *,
    old_path: str | None,
    new_path: str | None,
) -> list[str] | None:
    if all((not line) or line[0] in {" ", "+", "-"} for line in body_lines):
        return body_lines

    inferred_prefix: str | None = None
    if old_path is None and new_path is not None:
        inferred_prefix = "+"
    elif new_path is None and old_path is not None:
        inferred_prefix = "-"
    if inferred_prefix is None:
        return None

    normalized: list[str] = []
    for line in body_lines:
        if line and line[0] in {" ", "+", "-"}:
            normalized.append(line)
            continue
        normalized.append(f"{inferred_prefix}{line}")
    return normalized


def _render_unified_diff_block(
    *,
    source_text: str,
    target_text: str,
    old_path: str | None,
    new_path: str | None,
    target_path: str,
) -> str | None:
    diff_lines = list(
        difflib.unified_diff(
            source_text.splitlines(),
            target_text.splitlines(),
            fromfile=f"a/{old_path}" if old_path else "/dev/null",
            tofile=f"b/{new_path}" if new_path else "/dev/null",
            lineterm="",
        )
    )
    if not diff_lines:
        return None
    block_lines = [
        f"diff --git a/{old_path or target_path} b/{new_path or target_path}"
    ]
    if old_path is None:
        block_lines.append("new file mode 100644")
    if new_path is None:
        block_lines.append("deleted file mode 100644")
    block_lines.extend(diff_lines)
    return "\n".join(block_lines)


async def _reset_repo(repo_dir: Path) -> None:
    await _run_exec(
        ["git", "reset", "--hard", "HEAD"], cwd=repo_dir, timeout_seconds=30
    )
    await _run_exec(["git", "clean", "-fd"], cwd=repo_dir, timeout_seconds=30)


async def _run_shell_command(
    *,
    command: str,
    cwd: Path,
    timeout_seconds: int,
) -> CommandResult:
    process = await asyncio.create_subprocess_exec(
        "bash",
        "-lc",
        command,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout_seconds,
        )
    except TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise CodespaceSpecializerRuntimeError(
            f"codespace_command_timeout:{command}"
        ) from exc
    return CommandResult(
        exit_code=int(process.returncode or 0),
        stdout=(stdout_bytes or b"").decode("utf-8", errors="replace"),
        stderr=(stderr_bytes or b"").decode("utf-8", errors="replace"),
    )


async def _run_exec(
    argv: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> CommandResult:
    process = await asyncio.create_subprocess_exec(
        *argv,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout_seconds,
        )
    except TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise CodespaceSpecializerRuntimeError(
            f"codespace_exec_timeout:{' '.join(argv)}"
        ) from exc
    return CommandResult(
        exit_code=int(process.returncode or 0),
        stdout=(stdout_bytes or b"").decode("utf-8", errors="replace"),
        stderr=(stderr_bytes or b"").decode("utf-8", errors="replace"),
    )


def _truncate_text(text: str | None, *, limit: int = _MAX_OUTPUT_CHARS) -> str:
    normalized = (text or "").strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}...[truncated]"


def _strip_fence(value: str) -> str:
    text = (value or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


__all__ = [
    "CodespaceBundleArtifact",
    "CodespaceSpecializerRuntimeError",
    "build_demo_bundle_artifact",
    "build_retryable_provider_fallback_bundle_artifact",
    "generate_codespace_bundle_artifact",
    "is_retryable_codespace_specializer_error",
    "resolve_codespace_spec",
]
