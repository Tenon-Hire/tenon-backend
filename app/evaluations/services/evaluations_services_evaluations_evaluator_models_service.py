"""Application module for evaluations services evaluations evaluator models service workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class DayEvaluationInput:
    """Represent day evaluation input data and behavior."""

    day_index: int
    task_id: int | None
    task_type: str | None
    submission_id: int | None
    content_text: str | None
    content_json: dict[str, Any] | None
    repo_full_name: str | None
    commit_sha: str | None
    workflow_run_id: str | None
    diff_summary: dict[str, Any] | None
    tests_passed: int | None
    tests_failed: int | None
    transcript_reference: str | None
    transcript_segments: list[dict[str, Any]]
    cutoff_commit_sha: str | None
    eval_basis_ref: str | None


@dataclass(slots=True)
class EvaluationInputBundle:
    """Represent evaluation input bundle data and behavior."""

    candidate_session_id: int
    scenario_version_id: int
    model_name: str
    model_version: str
    prompt_version: str
    rubric_version: str
    disabled_day_indexes: list[int]
    day_inputs: list[DayEvaluationInput]
    simulation_context_json: dict[str, Any] | None = None
    ai_policy_snapshot_json: dict[str, Any] | None = None
    ai_policy_snapshot_digest: str | None = None
    company_prompt_overrides_json: dict[str, Any] | None = None
    simulation_prompt_overrides_json: dict[str, Any] | None = None


@dataclass(slots=True)
class DayEvaluationResult:
    """Represent day evaluation result data and behavior."""

    day_index: int
    score: float
    rubric_breakdown: dict[str, Any]
    evidence: list[dict[str, Any]]


@dataclass(slots=True)
class EvaluationResult:
    """Represent evaluation result data and behavior."""

    overall_fit_score: float
    recommendation: str
    confidence: float
    day_results: list[DayEvaluationResult]
    report_json: dict[str, Any]


class FitProfileEvaluator(Protocol):
    """Represent fit profile evaluator data and behavior."""

    async def evaluate(self, bundle: EvaluationInputBundle) -> EvaluationResult:
        """Execute evaluate."""
        ...


__all__ = [
    "DayEvaluationInput",
    "DayEvaluationResult",
    "EvaluationInputBundle",
    "EvaluationResult",
    "FitProfileEvaluator",
]
