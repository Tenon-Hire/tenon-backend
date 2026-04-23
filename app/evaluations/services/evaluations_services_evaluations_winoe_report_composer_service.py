"""Application module for evaluations services evaluations winoe report composer service workflows."""

from __future__ import annotations

from collections.abc import Mapping
from statistics import mean
from typing import Any

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EvaluationRun,
)

from .evaluations_services_evaluations_winoe_report_composer_day_scores_service import (
    _compose_day_scores,
)
from .evaluations_services_evaluations_winoe_report_composer_evidence_service import (
    _human_review_day_from_raw,
    _sanitize_evidence,
)
from .evaluations_services_evaluations_winoe_report_composer_normalize_service import (
    _normalize_datetime,
    _normalize_recommendation,
    _normalize_unit_interval,
)
from .evaluations_services_evaluations_winoe_report_composer_reviewer_reports_service import (
    _compose_reviewer_reports,
)


def compose_report(run: EvaluationRun) -> dict[str, Any]:
    """Execute compose report."""
    persisted_report = (
        dict(run.raw_report_json) if isinstance(run.raw_report_json, Mapping) else {}
    )
    day_scores = _compose_day_scores(run, persisted_report)
    reviewer_reports = _compose_reviewer_reports(run)
    scored_days = [
        day for day in day_scores if day.get("status") != "human_review_required"
    ]

    overall_winoe_score = _normalize_unit_interval(run.overall_winoe_score)
    if overall_winoe_score is None:
        report_score = _normalize_unit_interval(
            persisted_report.get("overallWinoeScore")
        )
        if report_score is not None:
            overall_winoe_score = report_score
        elif scored_days:
            overall_winoe_score = round(
                mean(
                    float(day["score"])
                    for day in scored_days
                    if day.get("score") is not None
                ),
                4,
            )
        else:
            overall_winoe_score = 0.0

    confidence = _normalize_unit_interval(run.confidence)
    if confidence is None:
        confidence = _normalize_unit_interval(persisted_report.get("confidence")) or 0.0

    report: dict[str, Any] = {
        "overallWinoeScore": overall_winoe_score,
        "recommendation": _normalize_recommendation(
            run.recommendation or persisted_report.get("recommendation")
        ),
        "confidence": confidence,
        "dayScores": day_scores,
        "reviewerReports": reviewer_reports,
        "version": {
            "model": run.model_name,
            "modelVersion": run.model_version,
            "promptVersion": run.prompt_version,
            "rubricVersion": run.rubric_version,
        },
    }

    metadata_json = run.metadata_json if isinstance(run.metadata_json, Mapping) else {}
    disabled_indexes = {
        int(value)
        for value in (metadata_json.get("disabledDayIndexes") or [])
        if isinstance(value, int) and 1 <= value <= 5
    }
    disabled_indexes.update(
        int(day["dayIndex"])
        for day in day_scores
        if day.get("status") == "human_review_required"
        and isinstance(day.get("dayIndex"), int)
    )
    if disabled_indexes:
        report["disabledDayIndexes"] = sorted(disabled_indexes)
    return report


def build_ready_payload(run: EvaluationRun) -> dict[str, Any]:
    """Build ready payload."""
    generated_at = _normalize_datetime(
        run.generated_at or run.completed_at or run.started_at
    )
    return {
        "status": "ready",
        "generatedAt": generated_at,
        "report": compose_report(run),
    }


__all__ = [
    "_human_review_day_from_raw",
    "_normalize_datetime",
    "_normalize_recommendation",
    "_normalize_unit_interval",
    "_sanitize_evidence",
    "build_ready_payload",
    "compose_report",
]
