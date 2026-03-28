"""Application module for evaluations services evaluations evaluator runtime service workflows."""

from __future__ import annotations

from app.evaluations.services.evaluations_services_evaluations_evaluator_evidence_service import (
    _build_day_evidence,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_models_service import (
    DayEvaluationResult,
    EvaluationInputBundle,
    EvaluationResult,
    FitProfileEvaluator,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_scoring_service import (
    _recommendation_from_score,
    _score_for_day,
)


class DeterministicFitProfileEvaluator:
    """Represent deterministic fit profile evaluator data and behavior."""

    async def evaluate(self, bundle: EvaluationInputBundle) -> EvaluationResult:
        """Execute evaluate."""
        disabled = set(bundle.disabled_day_indexes)
        day_results: list[DayEvaluationResult] = []
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
        overall, confidence = _aggregate_scores(day_results)
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


def _aggregate_scores(day_results: list[DayEvaluationResult]) -> tuple[float, float]:
    if not day_results:
        return 0.0, 0.0
    overall = round(sum(result.score for result in day_results) / len(day_results), 4)
    evidence_total = sum(len(result.evidence) for result in day_results)
    coverage = evidence_total / max(1, len(day_results) * 3)
    confidence = round(min(0.95, 0.45 + (coverage * 0.5)), 4)
    return overall, confidence


_default_evaluator: FitProfileEvaluator = DeterministicFitProfileEvaluator()


def get_fit_profile_evaluator() -> FitProfileEvaluator:
    """Return fit profile evaluator."""
    return _default_evaluator


__all__ = ["DeterministicFitProfileEvaluator", "get_fit_profile_evaluator"]
