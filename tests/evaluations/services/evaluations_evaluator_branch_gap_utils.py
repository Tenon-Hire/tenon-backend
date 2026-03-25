from __future__ import annotations

from app.evaluations.services import evaluator


def day_input(
    *,
    day_index: int,
    content_text: str | None = None,
    content_json: dict | None = None,
    repo_full_name: str | None = None,
    commit_sha: str | None = None,
    workflow_run_id: str | None = None,
    diff_summary: dict | None = None,
    tests_passed: int | None = None,
    tests_failed: int | None = None,
    transcript_reference: str | None = None,
    transcript_segments: list[dict] | None = None,
    cutoff_commit_sha: str | None = None,
) -> evaluator.DayEvaluationInput:
    return evaluator.DayEvaluationInput(
        day_index=day_index,
        task_id=day_index,
        task_type=f"day_{day_index}",
        submission_id=100 + day_index,
        content_text=content_text,
        content_json=content_json,
        repo_full_name=repo_full_name,
        commit_sha=commit_sha,
        workflow_run_id=workflow_run_id,
        diff_summary=diff_summary,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        transcript_reference=transcript_reference,
        transcript_segments=transcript_segments or [],
        cutoff_commit_sha=cutoff_commit_sha,
        eval_basis_ref=None,
    )
