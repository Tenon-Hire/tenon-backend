#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

PHASE_ALIASES = {
    "performance": "performance",
    "loc": "loc",
    "lines-of-code": "loc",
    "file-structure": "file-structure",
    "file-naming-structure": "file-structure",
    "testing-coverage": "testing-coverage",
    "testing": "testing-coverage",
    "documentation": "documentation",
}
PHASES = ("performance", "loc", "file-structure", "testing-coverage", "documentation")


@dataclass(frozen=True)
class HarnessResult:
    phase: str
    run_directory: str
    manifest_path: str
    copied_artifact_count: int
    skipped_paths: list[str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_phase(value: str) -> str:
    key = (value or "").strip().lower()
    if key in PHASE_ALIASES:
        return PHASE_ALIASES[key]
    raise ValueError(
        f"Unsupported phase '{value}'. Allowed: {', '.join(sorted(PHASE_ALIASES))}"
    )


def _safe_label(value: str) -> str:
    return (
        "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value)
        .strip("-_")
        .lower()
    )


def _git_value(args: list[str]) -> str | None:
    try:
        output = subprocess.check_output(
            ["git", *args], cwd=_repo_root(), stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return None
    return output or None


def _resolve_artifacts(
    repo_root: Path, paths: list[str], globs: list[str]
) -> list[Path]:
    explicit = [
        (
            Path(raw).expanduser()
            if Path(raw).is_absolute()
            else (repo_root / raw).resolve()
        )
        for raw in paths
    ]
    globbed = [
        candidate.resolve()
        for pattern in globs
        for candidate in sorted(repo_root.glob(pattern))
    ]
    resolved, seen = [], set()
    for path in [*explicit, *globbed]:
        if path not in seen:
            resolved.append(path)
            seen.add(path)
    return resolved


def _copy_artifact(repo_root: Path, src: Path, artifacts_dir: Path) -> str:
    destination = artifacts_dir / (
        src.relative_to(repo_root) if src.is_relative_to(repo_root) else src.name
    )
    if src.is_dir():
        shutil.copytree(src, destination, dirs_exist_ok=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, destination)
    return str(destination)


def create_run(
    *,
    phase_input: str,
    date_override: str | None,
    label: str | None,
    artifact_paths: list[str],
    artifact_globs: list[str],
) -> HarnessResult:
    repo_root, phase = _repo_root(), _resolve_phase(phase_input)
    phase_dir = repo_root / "code-quality" / phase
    for phase_name in PHASES:
        (repo_root / "code-quality" / phase_name).mkdir(parents=True, exist_ok=True)

    run_date = (date_override or datetime.now().strftime("%Y-%m-%d")).strip()
    run_name = f"{run_date}_{_safe_label(label or '')}".rstrip("_")
    run_dir = phase_dir / run_name
    if run_dir.exists():
        run_dir = phase_dir / f"{run_name}_{datetime.now().strftime('%H%M%S')}"
    artifacts_dir, notes_dir = run_dir / "artifacts", run_dir / "notes"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    notes_dir.mkdir(parents=True, exist_ok=True)

    latest_link = phase_dir / "latest"
    if latest_link.is_symlink() or latest_link.exists():
        latest_link.unlink()
    latest_link.symlink_to(run_dir.name)

    copied_artifacts, skipped_paths = [], []
    for src in _resolve_artifacts(repo_root, artifact_paths, artifact_globs):
        if src.exists():
            copied_artifacts.append(_copy_artifact(repo_root, src, artifacts_dir))
        else:
            skipped_paths.append(str(src))

    manifest_path = run_dir / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "phase": phase,
                "runId": run_dir.name,
                "runDate": run_date,
                "createdAt": datetime.now().astimezone().isoformat(),
                "createdBy": "scripts/code_quality_harness.py",
                "git": {
                    "branch": _git_value(["rev-parse", "--abbrev-ref", "HEAD"]),
                    "commit": _git_value(["rev-parse", "HEAD"]),
                },
                "copiedArtifacts": copied_artifacts,
                "skippedPaths": skipped_paths,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return HarnessResult(
        phase=phase,
        run_directory=str(run_dir),
        manifest_path=str(manifest_path),
        copied_artifact_count=len(copied_artifacts),
        skipped_paths=skipped_paths,
    )


def main() -> None:
    from code_quality_harness_args import parse_args

    args = parse_args()
    result = create_run(
        phase_input=args.phase,
        date_override=args.date,
        label=args.label,
        artifact_paths=args.artifact,
        artifact_globs=args.artifact_glob,
    )
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
