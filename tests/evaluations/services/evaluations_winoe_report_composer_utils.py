from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace

from app.evaluations.services import (
    evaluations_services_evaluations_winoe_report_composer_service as winoe_report_composer,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_composer_normalize_service import (
    WINOE_REPORT_RECOMMENDATION_LIMITED_SIGNAL,
    WINOE_REPORT_RECOMMENDATION_MIXED_SIGNAL,
)


def _row(
    *,
    day_index: int,
    score: float,
    rubric_results_json=None,
    evidence_pointers_json=None,
):
    return SimpleNamespace(
        day_index=day_index,
        score=score,
        rubric_results_json=rubric_results_json,
        evidence_pointers_json=evidence_pointers_json,
    )


def _run(
    *,
    overall_winoe_score=None,
    recommendation=None,
    confidence=None,
    raw_report_json=None,
    metadata_json=None,
    day_scores=None,
    generated_at=None,
    completed_at=None,
    started_at=None,
):
    return SimpleNamespace(
        overall_winoe_score=overall_winoe_score,
        recommendation=recommendation,
        confidence=confidence,
        raw_report_json=raw_report_json,
        metadata_json=metadata_json,
        day_scores=day_scores or [],
        model_name="fit-model",
        model_version="2026-03-12",
        prompt_version="winoe-report-v1",
        rubric_version="rubric-v1",
        generated_at=generated_at,
        completed_at=completed_at,
        started_at=started_at or datetime(2026, 3, 12, 12, 0),
    )


__all__ = [name for name in globals() if not name.startswith("__")]
