from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.repositories.evaluations.models import (
    EVALUATION_RECOMMENDATION_HIRE,
    EVALUATION_RECOMMENDATION_LEAN_HIRE,
    EVALUATION_RECOMMENDATION_NO_HIRE,
    EVALUATION_RECOMMENDATION_STRONG_HIRE,
)

_REPO_FULL_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


@dataclass(slots=True)
class DayEvaluationInput:
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
    candidate_session_id: int
    scenario_version_id: int
    model_name: str
    model_version: str
    prompt_version: str
    rubric_version: str
    disabled_day_indexes: list[int]
    day_inputs: list[DayEvaluationInput]


@dataclass(slots=True)
class DayEvaluationResult:
    day_index: int
    score: float
    rubric_breakdown: dict[str, Any]
    evidence: list[dict[str, Any]]


@dataclass(slots=True)
class EvaluationResult:
    overall_fit_score: float
    recommendation: str
    confidence: float
    day_results: list[DayEvaluationResult]
    report_json: dict[str, Any]


class FitProfileEvaluator(Protocol):
    async def evaluate(self, bundle: EvaluationInputBundle) -> EvaluationResult:
        ...


def _safe_repo_full_name(repo_full_name: str | None) -> str | None:
    if not isinstance(repo_full_name, str):
        return None
    normalized = repo_full_name.strip()
    if not _REPO_FULL_NAME_RE.match(normalized):
        return None
    return normalized


def _to_excerpt(value: str | None, *, max_chars: int = 280) -> str | None:
    if not isinstance(value, str):
        return None
    compact = " ".join(value.split())
    if not compact:
        return None
    return compact[:max_chars]


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _segment_start_ms(segment: dict[str, Any]) -> int | None:
    for key in ("startMs", "start_ms", "start"):
        value = _safe_int(segment.get(key))
        if value is not None:
            return max(0, value)
    return None


def _segment_end_ms(segment: dict[str, Any]) -> int | None:
    for key in ("endMs", "end_ms", "end"):
        value = _safe_int(segment.get(key))
        if value is not None:
            return max(0, value)
    return None


def _segment_text(segment: dict[str, Any]) -> str | None:
    for key in ("text", "content", "excerpt"):
        value = segment.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _score_for_day(
    day: DayEvaluationInput, evidence: Sequence[dict[str, Any]]
) -> float:
    score = 0.08
    score += min(0.4, 0.12 * len(evidence))

    kinds = {str(item.get("kind", "")) for item in evidence}
    if day.day_index in {1, 5}:
        excerpt = _to_excerpt(day.content_text)
        if excerpt is None and day.content_json is not None:
            excerpt = _to_excerpt(str(day.content_json))
        if excerpt:
            score += min(0.42, len(excerpt) / 700)
    elif day.day_index in {2, 3}:
        if "commit" in kinds:
            score += 0.2
        if "diff" in kinds:
            score += 0.12
        if "test" in kinds:
            passed = day.tests_passed if isinstance(day.tests_passed, int) else 0
            failed = day.tests_failed if isinstance(day.tests_failed, int) else 0
            total = passed + failed
            ratio = (passed / total) if total > 0 else 0.5
            score += 0.08 + (0.15 * ratio)
    elif day.day_index == 4:
        transcript_chars = sum(
            len(_to_excerpt(_segment_text(segment), max_chars=200) or "")
            for segment in day.transcript_segments[:4]
        )
        if transcript_chars > 0:
            score += min(0.5, transcript_chars / 1200)

    return round(max(0.0, min(1.0, score)), 4)


def _recommendation_from_score(score: float) -> str:
    if score >= 0.85:
        return EVALUATION_RECOMMENDATION_STRONG_HIRE
    if score >= 0.7:
        return EVALUATION_RECOMMENDATION_HIRE
    if score >= 0.55:
        return EVALUATION_RECOMMENDATION_LEAN_HIRE
    return EVALUATION_RECOMMENDATION_NO_HIRE


def _build_day_evidence(day: DayEvaluationInput) -> list[dict[str, Any]]:
    repo_full_name = _safe_repo_full_name(day.repo_full_name)
    evidence: list[dict[str, Any]] = []

    if day.day_index in {1, 5}:
        excerpt = _to_excerpt(day.content_text)
        if excerpt is None and day.content_json is not None:
            excerpt = _to_excerpt(str(day.content_json))
        if excerpt is not None:
            evidence.append(
                {
                    "kind": "reflection",
                    "ref": str(day.submission_id or f"day-{day.day_index}"),
                    "excerpt": excerpt,
                }
            )
    elif day.day_index in {2, 3}:
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
    elif day.day_index == 4:
        for segment in day.transcript_segments[:3]:
            if not isinstance(segment, dict):
                continue
            start_ms = _segment_start_ms(segment)
            end_ms = _segment_end_ms(segment)
            if start_ms is None or end_ms is None:
                continue
            if end_ms < start_ms:
                end_ms = start_ms
            excerpt = _to_excerpt(_segment_text(segment), max_chars=220)
            transcript_item: dict[str, Any] = {
                "kind": "transcript",
                "ref": str(
                    day.transcript_reference or day.submission_id or "transcript"
                ),
                "startMs": start_ms,
                "endMs": end_ms,
            }
            if excerpt is not None:
                transcript_item["excerpt"] = excerpt
            evidence.append(transcript_item)

    if not evidence:
        evidence.append(
            {
                "kind": "reflection",
                "ref": str(day.submission_id or f"day-{day.day_index}"),
                "excerpt": "No substantive evidence was available for this day at evaluation time.",
            }
        )

    return evidence


class DeterministicFitProfileEvaluator:
    async def evaluate(self, bundle: EvaluationInputBundle) -> EvaluationResult:
        disabled = set(bundle.disabled_day_indexes)
        day_results: list[DayEvaluationResult] = []
        report_day_scores: list[dict[str, Any]] = []

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
            evidence = _build_day_evidence(day_input)
            score = _score_for_day(day_input, evidence)
            rubric_breakdown = {
                "signalStrength": score,
                "evidenceCount": len(evidence),
                "taskType": day_input.task_type,
            }
            day_results.append(
                DayEvaluationResult(
                    day_index=day_input.day_index,
                    score=score,
                    rubric_breakdown=rubric_breakdown,
                    evidence=evidence,
                )
            )
            report_day_scores.append(
                {
                    "dayIndex": day_input.day_index,
                    "score": score,
                    "rubricBreakdown": dict(rubric_breakdown),
                    "evidence": list(evidence),
                    "status": "scored",
                }
            )

        enabled_count = len(day_results)
        if enabled_count:
            overall = round(
                sum(result.score for result in day_results) / enabled_count, 4
            )
            evidence_total = sum(len(result.evidence) for result in day_results)
            coverage = evidence_total / max(1, enabled_count * 3)
            confidence = round(min(0.95, 0.45 + (coverage * 0.5)), 4)
        else:
            overall = 0.0
            confidence = 0.0

        recommendation = _recommendation_from_score(overall)
        report_json = {
            "overallFitScore": overall,
            "recommendation": recommendation,
            "confidence": confidence,
            "dayScores": report_day_scores,
            "disabledDayIndexes": sorted(bundle.disabled_day_indexes),
            "version": {
                "model": bundle.model_name,
                "modelVersion": bundle.model_version,
                "promptVersion": bundle.prompt_version,
                "rubricVersion": bundle.rubric_version,
            },
        }
        return EvaluationResult(
            overall_fit_score=overall,
            recommendation=recommendation,
            confidence=confidence,
            day_results=day_results,
            report_json=report_json,
        )


_default_evaluator: FitProfileEvaluator = DeterministicFitProfileEvaluator()


def get_fit_profile_evaluator() -> FitProfileEvaluator:
    return _default_evaluator


__all__ = [
    "DayEvaluationInput",
    "DayEvaluationResult",
    "DeterministicFitProfileEvaluator",
    "EvaluationInputBundle",
    "EvaluationResult",
    "FitProfileEvaluator",
    "get_fit_profile_evaluator",
]
