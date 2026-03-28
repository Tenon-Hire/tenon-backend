"""Application module for evaluations services evaluations evaluator evidence code service workflows."""

from __future__ import annotations

from typing import Any

from app.evaluations.services.evaluations_services_evaluations_evaluator_helpers_service import (
    _safe_repo_full_name,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_models_service import (
    DayEvaluationInput,
)


def _build_code_day_evidence(day: DayEvaluationInput) -> list[dict[str, Any]]:
    repo_full_name = _safe_repo_full_name(day.repo_full_name)
    evidence: list[dict[str, Any]] = []
    commit_ref = (day.cutoff_commit_sha or day.commit_sha or "").strip() or None
    if commit_ref is not None:
        commit_item: dict[str, Any] = {
            "kind": "commit",
            "ref": commit_ref,
            "excerpt": f"Cutoff commit captured for day {day.day_index}.",
        }
        if repo_full_name:
            commit_item[
                "url"
            ] = f"https://github.com/{repo_full_name}/commit/{commit_ref}"
        evidence.append(commit_item)

    diff_summary = day.diff_summary if isinstance(day.diff_summary, dict) else {}
    base_ref = diff_summary.get("base")
    head_ref = diff_summary.get("head")
    if isinstance(base_ref, str) and isinstance(head_ref, str):
        diff_item: dict[str, Any] = {
            "kind": "diff",
            "ref": f"{base_ref}...{head_ref}",
            "excerpt": "Code delta between base and submitted head commits.",
        }
        if repo_full_name:
            diff_item[
                "url"
            ] = f"https://github.com/{repo_full_name}/compare/{base_ref}...{head_ref}"
        evidence.append(diff_item)

    if isinstance(day.tests_passed, int) or isinstance(day.tests_failed, int):
        passed = day.tests_passed if isinstance(day.tests_passed, int) else 0
        failed = day.tests_failed if isinstance(day.tests_failed, int) else 0
        test_item: dict[str, Any] = {
            "kind": "test",
            "ref": str(
                day.workflow_run_id or day.submission_id or f"day-{day.day_index}"
            ),
            "excerpt": f"Tests summary: passed={passed}, failed={failed}.",
        }
        if (
            repo_full_name
            and isinstance(day.workflow_run_id, str)
            and day.workflow_run_id.strip()
        ):
            test_item[
                "url"
            ] = f"https://github.com/{repo_full_name}/actions/runs/{day.workflow_run_id.strip()}"
        evidence.append(test_item)
    return evidence


__all__ = ["_build_code_day_evidence"]
