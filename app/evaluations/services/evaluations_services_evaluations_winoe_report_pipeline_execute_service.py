"""Application module for evaluations services evaluations winoe report pipeline execute service workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.evaluations.services.evaluations_services_evaluations_runs_coercion_service import (
    coerce_unit_interval_score,
)
from app.notifications.services import service as notification_service


def _build_day_scores(result) -> list[dict[str, Any]]:
    day_scores: list[dict[str, Any]] = []
    for day_result in result.day_results:
        rubric_breakdown = getattr(day_result, "rubric_breakdown", None)
        evidence = getattr(day_result, "evidence", None)
        score = coerce_unit_interval_score(
            getattr(day_result, "score", None),
            field_name=f"day_results[{day_result.day_index}].score",
            required=True,
        )
        if not isinstance(rubric_breakdown, dict) or not rubric_breakdown:
            raise ValueError(
                f"day_results[{day_result.day_index}] rubric_breakdown must be a non-empty object."
            )
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(
                f"day_results[{day_result.day_index}] evidence must be a non-empty list."
            )
        day_scores.append(
            {
                "day_index": day_result.day_index,
                "score": score,
                "rubric_results_json": rubric_breakdown,
                "evidence_pointers_json": evidence,
            }
        )
    return day_scores


async def _evaluate_and_finalize_run(
    *,
    db,
    run,
    evaluator,
    bundle,
    evaluation_runs,
    winoe_report_repository,
    context,
    run_metadata: dict[str, Any],
):
    result = await evaluator.evaluate(bundle)
    day_scores = _build_day_scores(result)
    completed_run = await evaluation_runs.complete_run(
        db,
        run_id=run.id,
        day_scores=day_scores,
        overall_winoe_score=result.overall_winoe_score,
        recommendation=result.recommendation,
        confidence=result.confidence,
        raw_report_json=result.report_json,
        metadata_json=run_metadata,
        allow_empty_day_scores=True,
        commit=False,
    )
    marker_generated_at = completed_run.generated_at or datetime.now(UTC)
    await winoe_report_repository.upsert_marker(
        db,
        candidate_session_id=context.candidate_session.id,
        generated_at=marker_generated_at,
        commit=False,
    )
    await notification_service.enqueue_winoe_report_ready_notification(
        db,
        candidate_session_id=context.candidate_session.id,
        trial_id=context.candidate_session.trial_id,
        commit=False,
    )
    await db.commit()
    return completed_run


async def _mark_failed_run(*, db, run, evaluation_runs, run_metadata: dict[str, Any]):
    await evaluation_runs.fail_run(
        db,
        run_id=run.id,
        error_code="evaluation_failed",
        error_message="evaluation_run_failed",
        metadata_json=run_metadata,
        commit=False,
    )
    await db.commit()


__all__ = ["_evaluate_and_finalize_run", "_mark_failed_run"]
