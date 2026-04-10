"""Application module for evaluations services evaluations winoe report pipeline execute service workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.notifications.services import service as notification_service


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
    day_scores = [
        {
            "day_index": day_result.day_index,
            "score": day_result.score,
            "rubric_results_json": day_result.rubric_breakdown,
            "evidence_pointers_json": day_result.evidence,
        }
        for day_result in result.day_results
    ]
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
