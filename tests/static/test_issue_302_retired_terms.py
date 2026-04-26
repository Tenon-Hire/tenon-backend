from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

RETIRED_TERMS = (
    "sim" + "_service",
    "Fit " + "Profile",
    "Fit " + "Score",
    "fit" + "_profile_ready_notification",
    "presentation" + "/upload",
    "debugging " + "exercise",
    "template" + "_catalog",
    "winoe" + "-template",
    "template" + "_repository",
    "template" + "Key",
    "tech" + "Stack",
    "special" + "izor",
    "Special" + "izor",
    "pre" + "commit",
    "codespace" + "_spec",
    "codespace " + "specification",
)

ALLOWLIST_BY_PATH: dict[Path, tuple[str, ...]] = {
    Path("app/core/db/migrations/reconcile_202603190001/specs_columns.py"): (
        "pre" + "commit",
    ),
    Path(
        "app/trials/repositories/scenario_versions/"
        "trials_repositories_scenario_versions_trials_scenario_versions_model.py"
    ): ("codespace" + "_spec",),
    Path("tests/ai/test_ai_prompt_pack_code_implementation_reviewer_service.py"): (
        "pre" + "commit",
        "special" + "izor",
    ),
    Path("tests/trials/services/test_trials_create_validation_service.py"): (
        "template" + "Key",
        "template" + "_repository",
        "tech" + "Stack",
    ),
}


def _scan_paths(repo_root: Path) -> Iterable[Path]:
    for directory in ("app", "scripts", "tests/static"):
        root = repo_root / directory
        if root.exists():
            yield from root.rglob("*.py")
    for path in (repo_root / "README.md",):
        if path.exists():
            yield path


def test_active_code_and_static_guards_do_not_reintroduce_retired_terms() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    failures: list[str] = []
    for path in sorted(set(_scan_paths(repo_root))):
        relative_path = path.relative_to(repo_root)
        allowed_terms = ALLOWLIST_BY_PATH.get(relative_path, ())
        text = path.read_text(encoding="utf-8")
        for term in RETIRED_TERMS:
            if term not in allowed_terms and term in text:
                failures.append(f"{relative_path}: {term}")

    assert failures == []
