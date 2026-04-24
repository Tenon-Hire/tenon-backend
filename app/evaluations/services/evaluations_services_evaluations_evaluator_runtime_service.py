"""Application module for evaluations services evaluations evaluator runtime service workflows."""

from __future__ import annotations

import json

from app.ai import (
    allow_demo_or_test_mode,
    build_required_snapshot_prompt,
    require_agent_policy_snapshot,
    require_agent_runtime,
    require_ai_policy_snapshot,
    validate_ai_policy_snapshot_contract,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_evidence_service import (
    _build_day_evidence,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_models_service import (
    DayEvaluationResult,
    EvaluationInputBundle,
    EvaluationResult,
    ReviewerReportResult,
    WinoeReportEvaluator,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_scoring_service import (
    _recommendation_from_score,
    _score_for_day,
)
from app.integrations.winoe_report_review import (
    WinoeReportAggregateRequest,
    WinoeReportDayReviewRequest,
    get_winoe_report_review_provider,
)


class DeterministicWinoeReportEvaluator:
    """Represent deterministic winoe report evaluator data and behavior."""

    async def evaluate(self, bundle: EvaluationInputBundle) -> EvaluationResult:
        """Execute evaluate."""
        snapshot = require_ai_policy_snapshot(
            bundle.ai_policy_snapshot_json,
            scenario_version_id=bundle.scenario_version_id,
        )
        validate_ai_policy_snapshot_contract(
            snapshot,
            scenario_version_id=bundle.scenario_version_id,
        )
        disabled = set(bundle.disabled_day_indexes)
        day_results: list[DayEvaluationResult] = []
        reviewer_reports: list[ReviewerReportResult] = []
        report_day_scores: list[dict[str, object]] = []
        for day_input in sorted(bundle.day_inputs, key=lambda value: value.day_index):
            if day_input.day_index in disabled:
                report_day_scores.append(
                    {
                        "dayIndex": day_input.day_index,
                        "status": "human_review_required",
                        "reason": "ai_eval_disabled_for_day",
                    }
                )
                continue
            day_result, reviewer_report = _deterministic_day_review(day_input)
            day_results.append(day_result)
            reviewer_reports.append(reviewer_report)
            report_day_scores.append(
                {
                    "dayIndex": day_result.day_index,
                    "score": day_result.score,
                    "rubricBreakdown": dict(day_result.rubric_breakdown),
                    "evidence": list(day_result.evidence),
                    "status": "scored",
                }
            )
        report_json = _deterministic_aggregate_report(
            bundle=bundle,
            snapshot_json=snapshot,
            day_results=day_results,
            reviewer_reports=reviewer_reports,
            report_day_scores=report_day_scores,
        )
        return EvaluationResult(
            overall_winoe_score=float(report_json["overallWinoeScore"]),
            recommendation=str(report_json["recommendation"]),
            confidence=float(report_json["confidence"]),
            day_results=day_results,
            report_json=report_json,
            reviewer_reports=reviewer_reports,
        )


class LiveWinoeReportEvaluator:
    """Provider-backed winoe report evaluator with per-day reviewer orchestration."""

    async def evaluate(self, bundle: EvaluationInputBundle) -> EvaluationResult:
        """Execute evaluate."""
        snapshot = require_ai_policy_snapshot(
            bundle.ai_policy_snapshot_json,
            scenario_version_id=bundle.scenario_version_id,
        )
        validate_ai_policy_snapshot_contract(
            snapshot,
            scenario_version_id=bundle.scenario_version_id,
        )
        disabled = set(bundle.disabled_day_indexes)
        day_results: list[DayEvaluationResult] = []
        reviewer_reports: list[ReviewerReportResult] = []
        report_day_scores: list[dict[str, object]] = []

        for day_input in sorted(bundle.day_inputs, key=lambda value: value.day_index):
            if day_input.day_index in disabled:
                report_day_scores.append(
                    {
                        "dayIndex": day_input.day_index,
                        "status": "human_review_required",
                        "reason": "ai_eval_disabled_for_day",
                    }
                )
                continue
            reviewer_key = _reviewer_key_for_day(day_input.day_index)
            require_agent_policy_snapshot(
                snapshot,
                reviewer_key,
                scenario_version_id=bundle.scenario_version_id,
            )
            reviewer_runtime = require_agent_runtime(
                snapshot,
                reviewer_key,
                scenario_version_id=bundle.scenario_version_id,
            )
            reviewer_runtime_mode = str(reviewer_runtime["runtimeMode"])
            reviewer_provider = str(reviewer_runtime["provider"])
            reviewer_model = str(reviewer_runtime["model"])
            if allow_demo_or_test_mode(reviewer_runtime_mode):
                day_result, reviewer_report = _deterministic_day_review(day_input)
            else:
                run_context_md = _build_day_run_context(bundle, day_input)
                system_prompt, rubric_prompt = build_required_snapshot_prompt(
                    snapshot_json=snapshot,
                    agent_key=reviewer_key,
                    run_context_md=run_context_md,
                    scenario_version_id=bundle.scenario_version_id,
                )
                request = WinoeReportDayReviewRequest(
                    system_prompt=system_prompt,
                    user_prompt=_build_day_review_prompt(
                        bundle=bundle,
                        day_input=day_input,
                        rubric_prompt=rubric_prompt,
                    ),
                    model=reviewer_model,
                )
                provider = get_winoe_report_review_provider(reviewer_provider)
                reviewer_output = provider.review_day(request=request)
                reviewer_report = _reviewer_report_from_output(
                    reviewer_key=reviewer_key,
                    day_input=day_input,
                    reviewer_output=reviewer_output,
                )
                day_result = DayEvaluationResult(
                    day_index=reviewer_output.dayIndex,
                    score=reviewer_output.score,
                    rubric_breakdown=dict(reviewer_output.rubricBreakdown),
                    evidence=[
                        evidence.model_dump() for evidence in reviewer_output.evidence
                    ],
                )
            reviewer_reports.append(reviewer_report)
            day_results.append(day_result)
            report_day_scores.append(
                {
                    "dayIndex": day_result.day_index,
                    "score": day_result.score,
                    "rubricBreakdown": dict(day_result.rubric_breakdown),
                    "evidence": list(day_result.evidence),
                    "status": "scored",
                }
            )

        require_agent_policy_snapshot(
            snapshot,
            "winoeReport",
            scenario_version_id=bundle.scenario_version_id,
        )
        aggregator_runtime = require_agent_runtime(
            snapshot,
            "winoeReport",
            scenario_version_id=bundle.scenario_version_id,
        )
        aggregator_runtime_mode = str(aggregator_runtime["runtimeMode"])
        aggregator_provider = str(aggregator_runtime["provider"])
        aggregator_model = str(aggregator_runtime["model"])
        if allow_demo_or_test_mode(aggregator_runtime_mode) or not reviewer_reports:
            report_json = _deterministic_aggregate_report(
                bundle=bundle,
                snapshot_json=snapshot,
                day_results=day_results,
                reviewer_reports=reviewer_reports,
                report_day_scores=report_day_scores,
            )
        else:
            run_context_md = _build_winoe_report_run_context(bundle)
            system_prompt, rubric_prompt = build_required_snapshot_prompt(
                snapshot_json=snapshot,
                agent_key="winoeReport",
                run_context_md=run_context_md,
                scenario_version_id=bundle.scenario_version_id,
            )
            provider = get_winoe_report_review_provider(aggregator_provider)
            aggregate_output = provider.aggregate_winoe_report(
                request=WinoeReportAggregateRequest(
                    system_prompt=system_prompt,
                    user_prompt=json.dumps(
                        {
                            "trialContext": bundle.trial_context_json or {},
                            "reviewerReports": [
                                _reviewer_report_payload(report)
                                for report in reviewer_reports
                            ],
                            "disabledDayIndexes": sorted(bundle.disabled_day_indexes),
                            "rubricGuidance": rubric_prompt,
                        },
                        indent=2,
                        sort_keys=True,
                    ),
                    model=aggregator_model,
                )
            )
            merged_day_scores = _merge_day_scores(
                reviewer_day_scores=report_day_scores,
                aggregator_day_scores=[
                    day_score.model_dump() for day_score in aggregate_output.dayScores
                ],
            )
            report_json = {
                "overallWinoeScore": aggregate_output.overallWinoeScore,
                "recommendation": aggregate_output.recommendation,
                "confidence": aggregate_output.confidence,
                "dayScores": merged_day_scores,
                "strengths": list(aggregate_output.strengths),
                "risks": list(aggregate_output.risks),
                "calibrationText": aggregate_output.calibrationText,
                "disabledDayIndexes": sorted(bundle.disabled_day_indexes),
                "reviewerReports": [
                    _reviewer_report_payload(report) for report in reviewer_reports
                ],
                "version": {
                    "scenarioVersionId": bundle.scenario_version_id,
                    "model": bundle.model_name,
                    "modelVersion": bundle.model_version,
                    "provider": aggregator_provider,
                    "promptVersion": bundle.prompt_version,
                    "rubricVersion": bundle.rubric_version,
                    "aiPolicySnapshotDigest": (
                        bundle.ai_policy_snapshot_digest
                        or snapshot.get("snapshotDigest")
                    ),
                    "promptPackVersion": snapshot.get("promptPackVersion"),
                    "rubricSnapshots": snapshot.get("rubricSnapshots") or [],
                },
            }
        return EvaluationResult(
            overall_winoe_score=float(report_json["overallWinoeScore"]),
            recommendation=str(report_json["recommendation"]),
            confidence=float(report_json["confidence"]),
            day_results=day_results,
            report_json=report_json,
            reviewer_reports=reviewer_reports,
        )


def _reviewer_key_for_day(day_index: int) -> str:
    if day_index == 1:
        return "designDocReviewer"
    if day_index in {2, 3}:
        return "codeImplementationReviewer"
    if day_index == 4:
        return "demoPresentationReviewer"
    return "reflectionEssayReviewer"


def _submission_kind_for_day(day_input) -> str:
    task_type = getattr(day_input, "task_type", None)
    if isinstance(task_type, str) and task_type.strip():
        return task_type.strip().lower()
    if day_input.day_index in {2, 3}:
        return "code"
    if day_input.day_index == 4:
        return "transcript"
    return "text"


def _reviewer_report_from_output(
    *,
    reviewer_key: str,
    day_input,
    reviewer_output,
) -> ReviewerReportResult:
    return ReviewerReportResult(
        reviewer_agent_key=reviewer_key,
        day_index=reviewer_output.dayIndex,
        submission_kind=_submission_kind_for_day(day_input),
        score=float(reviewer_output.score),
        dimensional_scores_json=dict(reviewer_output.rubricBreakdown),
        evidence_citations_json=[
            evidence.model_dump() for evidence in reviewer_output.evidence
        ],
        assessment_text=str(reviewer_output.summary),
        strengths_json=[str(item) for item in reviewer_output.strengths],
        risks_json=[str(item) for item in reviewer_output.risks],
        raw_output_json=reviewer_output.model_dump(),
    )


def _reviewer_report_payload(report: ReviewerReportResult) -> dict[str, object]:
    return {
        "reviewerAgentKey": report.reviewer_agent_key,
        "dayIndex": report.day_index,
        "submissionKind": report.submission_kind,
        "score": report.score,
        "dimensionalScores": dict(report.dimensional_scores_json),
        "evidenceCitations": list(report.evidence_citations_json),
        "assessment": report.assessment_text,
        "strengths": list(report.strengths_json),
        "concerns": list(report.risks_json),
    }


def _build_day_run_context(
    bundle: EvaluationInputBundle,
    day_input,
) -> str:
    return (
        f"Candidate session ID: {bundle.candidate_session_id}\n"
        f"Scenario version ID: {bundle.scenario_version_id}\n"
        f"Day index: {day_input.day_index}\n"
        f"Task type: {day_input.task_type or 'unknown'}\n"
        f"Commit SHA: {day_input.commit_sha or 'n/a'}\n"
        f"Transcript ref: {day_input.transcript_reference or 'n/a'}"
    )


def _build_winoe_report_run_context(bundle: EvaluationInputBundle) -> str:
    return (
        f"Candidate session ID: {bundle.candidate_session_id}\n"
        f"Scenario version ID: {bundle.scenario_version_id}\n"
        f"Disabled day indexes: {sorted(bundle.disabled_day_indexes)}"
    )


def _build_day_review_prompt(
    *,
    bundle: EvaluationInputBundle,
    day_input,
    rubric_prompt: str,
) -> str:
    return json.dumps(
        {
            "trialContext": bundle.trial_context_json or {},
            "dayInput": {
                "dayIndex": day_input.day_index,
                "taskId": day_input.task_id,
                "taskType": day_input.task_type,
                "submissionId": day_input.submission_id,
                "contentText": day_input.content_text,
                "contentJson": day_input.content_json,
                "repoFullName": day_input.repo_full_name,
                "commitSha": day_input.commit_sha,
                "workflowRunId": day_input.workflow_run_id,
                "diffSummary": day_input.diff_summary,
                "testsPassed": day_input.tests_passed,
                "testsFailed": day_input.tests_failed,
                "transcriptReference": day_input.transcript_reference,
                "transcriptSegments": day_input.transcript_segments,
                "cutoffCommitSha": day_input.cutoff_commit_sha,
                "evalBasisRef": day_input.eval_basis_ref,
            },
            "rubricGuidance": rubric_prompt,
        },
        indent=2,
        sort_keys=True,
    )


def _deterministic_day_review(
    day_input,
) -> tuple[DayEvaluationResult, ReviewerReportResult]:
    evidence = _build_day_evidence(day_input)
    score = _score_for_day(day_input, evidence)
    rubric_breakdown = {
        "signalStrength": score,
        "evidenceCount": len(evidence),
        "taskType": day_input.task_type,
    }
    strengths: list[str] = []
    risks: list[str] = []
    if score >= 0.7:
        strengths.append("Strong evidence-backed execution signal")
    if day_input.tests_failed:
        risks.append("Observed failing automated tests")
    if not evidence:
        risks.append("Low direct evidence available")
    day_result = DayEvaluationResult(
        day_index=day_input.day_index,
        score=score,
        rubric_breakdown=rubric_breakdown,
        evidence=evidence,
    )
    reviewer_report = ReviewerReportResult(
        reviewer_agent_key=_reviewer_key_for_day(day_input.day_index),
        day_index=day_input.day_index,
        submission_kind=_submission_kind_for_day(day_input),
        score=score,
        dimensional_scores_json=dict(rubric_breakdown),
        evidence_citations_json=list(evidence),
        assessment_text="Deterministic demo/test reviewer output.",
        strengths_json=strengths,
        risks_json=risks,
        raw_output_json={
            "dayIndex": day_input.day_index,
            "score": score,
            "summary": "Deterministic demo/test reviewer output.",
            "rubricBreakdown": dict(rubric_breakdown),
            "evidence": list(evidence),
            "strengths": strengths,
            "risks": risks,
        },
    )
    return day_result, reviewer_report


def _deterministic_aggregate_report(
    *,
    bundle: EvaluationInputBundle,
    snapshot_json: dict[str, object],
    day_results: list[DayEvaluationResult],
    reviewer_reports: list[ReviewerReportResult],
    report_day_scores: list[dict[str, object]],
) -> dict[str, object]:
    overall, confidence = _aggregate_scores(day_results)
    strengths = _unique_strings(
        item
        for report in reviewer_reports
        for item in report.strengths_json
        if isinstance(item, str)
    )[:6]
    risks = _unique_strings(
        item
        for report in reviewer_reports
        for item in report.risks_json
        if isinstance(item, str)
    )[:6]
    return {
        "overallWinoeScore": overall,
        "recommendation": _recommendation_from_score(overall),
        "confidence": confidence,
        "dayScores": list(report_day_scores),
        "disabledDayIndexes": sorted(bundle.disabled_day_indexes),
        "strengths": strengths,
        "risks": risks,
        "calibrationText": "Deterministic demo/test aggregation.",
        "reviewerReports": [
            _reviewer_report_payload(report) for report in reviewer_reports
        ],
        "version": {
            "scenarioVersionId": bundle.scenario_version_id,
            "model": bundle.model_name,
            "modelVersion": bundle.model_version,
            "provider": str(
                snapshot_json["agents"]["winoeReport"]["runtime"]["provider"]
            ),
            "promptVersion": bundle.prompt_version,
            "rubricVersion": bundle.rubric_version,
            "aiPolicySnapshotDigest": (
                bundle.ai_policy_snapshot_digest or snapshot_json.get("snapshotDigest")
            ),
            "promptPackVersion": snapshot_json.get("promptPackVersion"),
            "rubricSnapshots": snapshot_json.get("rubricSnapshots") or [],
        },
    }


def _merge_day_scores(
    *,
    reviewer_day_scores: list[dict[str, object]],
    aggregator_day_scores: list[dict[str, object]],
) -> list[dict[str, object]]:
    merged: dict[int, dict[str, object]] = {}
    for item in reviewer_day_scores:
        day_index = item.get("dayIndex")
        if isinstance(day_index, int):
            merged[day_index] = dict(item)
    for item in aggregator_day_scores:
        day_index = item.get("dayIndex")
        if isinstance(day_index, int) and day_index not in merged:
            merged[day_index] = dict(item)
    return [merged[day] for day in sorted(merged)]


def _unique_strings(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _aggregate_scores(day_results: list[DayEvaluationResult]) -> tuple[float, float]:
    if not day_results:
        return 0.0, 0.0
    overall = round(sum(result.score for result in day_results) / len(day_results), 4)
    evidence_total = sum(len(result.evidence) for result in day_results)
    coverage = evidence_total / max(1, len(day_results) * 3)
    confidence = round(min(0.95, 0.45 + (coverage * 0.5)), 4)
    return overall, confidence


_default_evaluator: WinoeReportEvaluator = LiveWinoeReportEvaluator()


def get_winoe_report_evaluator() -> WinoeReportEvaluator:
    """Return winoe report evaluator."""
    return _default_evaluator


__all__ = [
    "DeterministicWinoeReportEvaluator",
    "LiveWinoeReportEvaluator",
    "get_winoe_report_evaluator",
]
