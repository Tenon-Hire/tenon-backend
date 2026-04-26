"""Application module for evaluations services evaluations evaluator models service workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class CodeImplementationEvidenceContext:
    """Represent repository/process evidence for Days 2 and 3."""

    repository_snapshot: dict[str, Any] | None = None
    repository_url: str | None = None
    repository_reference: str | None = None
    repository_artifact_references: list[dict[str, Any]] = field(default_factory=list)
    commit_history: list[dict[str, Any]] = field(default_factory=list)
    file_creation_timeline: list[dict[str, Any]] = field(default_factory=list)
    test_coverage_progression: list[dict[str, Any]] = field(default_factory=list)
    dependency_metadata: dict[str, Any] | None = None
    documentation_evolution: list[dict[str, Any]] = field(default_factory=list)
    evidence_status: dict[str, str] = field(default_factory=dict)


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
    code_implementation_evidence: CodeImplementationEvidenceContext = field(
        default_factory=CodeImplementationEvidenceContext
    )
    trial_context_json: dict[str, Any] | None = None
    ai_policy_snapshot_json: dict[str, Any] | None = None
    ai_policy_snapshot_digest: str | None = None
    company_prompt_overrides_json: dict[str, Any] | None = None
    trial_prompt_overrides_json: dict[str, Any] | None = None


@dataclass(slots=True)
class DayEvaluationResult:
    """Represent day evaluation result data and behavior."""

    day_index: int
    score: float
    rubric_breakdown: dict[str, Any]
    evidence: list[dict[str, Any]]


@dataclass(slots=True)
class ReviewerReportResult:
    """Represent persisted reviewer report data and behavior."""

    reviewer_agent_key: str
    day_index: int
    submission_kind: str
    score: float
    dimensional_scores_json: dict[str, Any]
    evidence_citations_json: list[dict[str, Any]]
    assessment_text: str
    strengths_json: list[str]
    risks_json: list[str]
    raw_output_json: dict[str, Any] | None = None


@dataclass(slots=True)
class EvaluationResult:
    """Represent evaluation result data and behavior."""

    overall_winoe_score: float
    recommendation: str
    confidence: float
    day_results: list[DayEvaluationResult]
    report_json: dict[str, Any]
    reviewer_reports: list[ReviewerReportResult] = field(default_factory=list)


class WinoeReportEvaluator(Protocol):
    """Represent winoe report evaluator data and behavior."""

    async def evaluate(self, bundle: EvaluationInputBundle) -> EvaluationResult:
        """Execute evaluate."""
        ...


__all__ = [
    "DayEvaluationInput",
    "DayEvaluationResult",
    "CodeImplementationEvidenceContext",
    "EvaluationInputBundle",
    "EvaluationResult",
    "ReviewerReportResult",
    "WinoeReportEvaluator",
]
