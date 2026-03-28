"""Application module for evaluations services evaluations fit profile composer day scores service workflows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EvaluationRun,
)

from .evaluations_services_evaluations_fit_profile_composer_evidence_service import (
    _human_review_day_from_raw,
    _sanitize_evidence,
)


def _compose_day_scores(
    run: EvaluationRun, persisted_report: Mapping[str, Any]
) -> list[dict[str, Any]]:
    scored_by_day: dict[int, dict[str, Any]] = {}
    for row in sorted(run.day_scores, key=lambda r: r.day_index):
        evidence = [
            sanitized
            for sanitized in (
                _sanitize_evidence(pointer)
                for pointer in (row.evidence_pointers_json or [])
            )
            if sanitized is not None
        ]
        scored_by_day[int(row.day_index)] = {
            "dayIndex": int(row.day_index),
            "score": float(row.score),
            "rubricBreakdown": dict(row.rubric_results_json or {}),
            "evidence": evidence,
            "status": "scored",
        }

    placeholder_days: dict[int, dict[str, Any]] = {}
    persisted_day_scores = persisted_report.get("dayScores")
    if isinstance(persisted_day_scores, list):
        for raw_day_score in persisted_day_scores:
            placeholder = _human_review_day_from_raw(raw_day_score)
            if placeholder is None:
                continue
            day_index = int(placeholder["dayIndex"])
            if day_index not in scored_by_day:
                placeholder_days[day_index] = placeholder

    payload: list[dict[str, Any]] = []
    for day_index in sorted(set(scored_by_day) | set(placeholder_days)):
        payload.append(scored_by_day.get(day_index) or placeholder_days[day_index])
    return payload
