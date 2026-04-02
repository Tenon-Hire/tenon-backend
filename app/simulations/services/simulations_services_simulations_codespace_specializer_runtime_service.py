"""Runtime helpers for codespace specialization bundle generation."""

from __future__ import annotations

import asyncio
import json
import logging
import os
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


def resolve_codespace_spec(scenario_version) -> CodespaceSpec:
    """Return a validated codespace spec with a backwards-compatible fallback."""
    raw_spec = getattr(scenario_version, "codespace_spec_json", None) or {}
    if raw_spec:
        return CodespaceSpec.model_validate(raw_spec)
    storyline = (getattr(scenario_version, "storyline_md", "") or "").strip()
    summary = storyline.splitlines()[0].strip("# ").strip() or "Simulation baseline"
    return CodespaceSpec(
        summary=summary,
        candidate_goal="Implement the scenario's shared Day 2/3 coding workspace.",
        acceptance_criteria=["Repository baseline matches the approved scenario."],
    )


def build_demo_bundle_artifact(
    *,
    scenario_version,
    template_repo_full_name: str,
) -> CodespaceBundleArtifact:
    """Build a deterministic bundle artifact for demo or test runtime modes."""
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
                    "path": "TENON_SIMULATION_CONTEXT.md",
                    "content": _build_demo_context_markdown(spec, template_repo_full_name),
                    "executable": False,
                }
            ]
        },
        indent=2,
        sort_keys=True,
    )
    provenance_json = {
        "mode": "demo_or_test",
        "templateRepoFullName": template_repo_full_name,
        "planMd": (
            "Create a single repository context file so candidate workspaces start with "
            "simulation-specific instructions without mutating product code."
        ),
        "unifiedDiff": None,
    }
    return CodespaceBundleArtifact(
        patch_payload_json=patch_payload_json,
        commit_message="chore: prepare simulation baseline",
        base_template_sha=None,
        model_name="deterministic-demo",
        model_version="deterministic-demo",
        prompt_version=str(codespace_snapshot["promptVersion"]),
        test_summary_json={
            "status": "skipped",
            "command": None,
            "attempts": [{"attempt": 1, "status": "skipped", "reason": "demo_or_test_mode"}],
        },
        provenance_json=provenance_json,
    )


async def generate_codespace_bundle_artifact(
    *,
    template_repo_full_name: str,
    scenario_version,
    simulation,
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
    spec = resolve_codespace_spec(scenario_version)
    template_clone_url = _build_clone_url(template_repo_full_name)

    with tempfile.TemporaryDirectory(prefix="tenon-codespace-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        repo_dir = temp_dir / "repo"
        await _clone_repo(
            repo_dir=repo_dir,
            clone_url=template_clone_url,
            timeout_seconds=int(runtime.get("timeoutSeconds", 0) or 0) or 300,
        )
        base_template_sha = await _git_head_sha(repo_dir)
        repo_snapshot = await _build_repo_snapshot(repo_dir, spec)
        run_context_md = _build_run_context(
            simulation=simulation,
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
            "simulation": {
                "id": getattr(simulation, "id", None),
                "title": getattr(simulation, "title", None),
                "role": getattr(simulation, "role", None),
                "techStack": getattr(simulation, "tech_stack", None),
                "focus": getattr(simulation, "focus", None),
                "companyContext": getattr(simulation, "company_context", None),
            },
            "scenarioVersion": {
                "id": getattr(scenario_version, "id", None),
                "versionIndex": getattr(scenario_version, "version_index", None),
                "templateKey": getattr(scenario_version, "template_key", None),
                "storylineMd": getattr(scenario_version, "storyline_md", None),
            },
            "codespaceSpec": spec.model_dump(),
            "rubricGuidance": rubric_prompt,
            "repositorySnapshot": repo_snapshot,
        }

        previous_failure: dict | None = None
        previous_proposal = None
        attempts: list[dict] = []

        for attempt in (1, 2):
            user_prompt = json.dumps(
                {
                    **prompt_payload,
                    "attempt": attempt,
                    "repairContext": previous_failure,
                },
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

            previous_proposal = proposal
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
                }
                attempts.append(
                    {
                        "attempt": attempt,
                        "status": "apply_failed",
                        "stdout": _truncate_text(apply_result.stdout),
                        "stderr": _truncate_text(apply_result.stderr),
                    }
                )
                if attempt == 1:
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
                    prompt_version=(
                        str(codespace_snapshot.get("promptVersion"))
                        if isinstance(codespace_snapshot, dict)
                        and isinstance(codespace_snapshot.get("promptVersion"), str)
                        else prompt_entry.prompt_version
                    ),
                    test_summary_json={
                        "status": "skipped",
                        "command": None,
                        "attempts": attempts
                        + [
                            {
                                "attempt": attempt,
                                "status": "skipped",
                                "reason": "missing_test_command",
                            }
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
                timeout_seconds=config.timeout_seconds,
            )
            attempts.append(
                {
                    "attempt": attempt,
                    "status": "passed"
                    if test_result.exit_code == 0
                    else "failed",
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
                    prompt_version=(
                        str(codespace_snapshot.get("promptVersion"))
                        if isinstance(codespace_snapshot, dict)
                        and isinstance(codespace_snapshot.get("promptVersion"), str)
                        else prompt_entry.prompt_version
                    ),
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
            }

        error_detail = previous_failure or {"failureType": "unknown"}
        raise CodespaceSpecializerRuntimeError(
            f"codespace_tests_failed:{json.dumps(error_detail, sort_keys=True)}"
        )


def _build_demo_context_markdown(
    spec: CodespaceSpec,
    template_repo_full_name: str,
) -> str:
    lines = [
        "# Tenon Simulation Context",
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
    simulation,
    scenario_version,
    template_repo_full_name: str,
    base_template_sha: str | None,
) -> str:
    return (
        f"Simulation ID: {getattr(simulation, 'id', None)}\n"
        f"Scenario version ID: {getattr(scenario_version, 'id', None)}\n"
        f"Template key: {getattr(scenario_version, 'template_key', None)}\n"
        f"Template repo: {template_repo_full_name}\n"
        f"Base template SHA: {base_template_sha or 'unknown'}"
    )


def _build_clone_url(repo_full_name: str) -> str:
    token = (os.environ.get("TENON_GITHUB_TOKEN") or "").strip()
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


async def _build_repo_snapshot(repo_dir: Path, spec: CodespaceSpec) -> dict:
    tracked_result = await _run_exec(
        ["git", "ls-files"],
        cwd=repo_dir,
        timeout_seconds=30,
    )
    if tracked_result.exit_code != 0:
        raise CodespaceSpecializerRuntimeError("codespace_ls_files_failed")
    tracked_files = [
        line.strip()
        for line in tracked_result.stdout.splitlines()
        if line.strip() and not _is_skipped_repo_path(line.strip())
    ]
    prioritized = _prioritize_paths(tracked_files, spec)
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
        "files": file_payloads,
        "truncated": len(file_payloads) < len(tracked_files),
    }


def _prioritize_paths(tracked_files: list[str], spec: CodespaceSpec) -> list[str]:
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
    wanted = list(dict.fromkeys([*spec.target_files, *base_priority]))
    priority_map = {path: index for index, path in enumerate(wanted)}
    return sorted(
        tracked_files,
        key=lambda path: (
            priority_map.get(path, len(priority_map) + 1),
            path not in spec.target_files,
            path,
        ),
    )


def _is_skipped_repo_path(path: str) -> bool:
    parts = path.split("/")
    return any(
        part in {"node_modules", "dist", "build", "coverage", ".next", ".git"}
        for part in parts
    )


async def _apply_unified_diff(*, repo_dir: Path, unified_diff: str) -> CommandResult:
    patch_path = repo_dir / ".tenon_specializer.patch"
    patch_path.write_text(_strip_fence(unified_diff), encoding="utf-8")
    try:
        return await _run_exec(
            [
                "git",
                "apply",
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
        return spec.test_command.strip() or None
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
        return "pytest"
    if (repo_dir / "go.mod").exists():
        return "go test ./..."
    if (repo_dir / "Cargo.toml").exists():
        return "cargo test"
    return None


async def _reset_repo(repo_dir: Path) -> None:
    await _run_exec(["git", "reset", "--hard", "HEAD"], cwd=repo_dir, timeout_seconds=30)
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
    "generate_codespace_bundle_artifact",
    "resolve_codespace_spec",
]
