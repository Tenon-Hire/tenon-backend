from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from statistics import mean
from typing import Any

from app.repositories.evaluations.models import (
    EVALUATION_RECOMMENDATION_LEAN_HIRE,
    EVALUATION_RECOMMENDATIONS,
    EvaluationRun,
)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_unit_interval(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    normalized = float(value)
    if normalized < 0 or normalized > 1:
        return None
    return round(normalized, 4)


def _normalize_recommendation(value: Any) -> str:
    if not isinstance(value, str):
        return EVALUATION_RECOMMENDATION_LEAN_HIRE
    normalized = value.strip().lower()
    if normalized not in EVALUATION_RECOMMENDATIONS:
        return EVALUATION_RECOMMENDATION_LEAN_HIRE
    return normalized


def _sanitize_evidence(pointer: Any) -> dict[str, Any] | None:
    if not isinstance(pointer, Mapping):
        return None

    kind_raw = pointer.get("kind")
    if not isinstance(kind_raw, str) or not kind_raw.strip():
        return None

    sanitized: dict[str, Any] = {"kind": kind_raw.strip()}
    ref_value = pointer.get("ref")
    if isinstance(ref_value, str) and ref_value.strip():
        sanitized["ref"] = ref_value.strip()

    url_value = pointer.get("url")
    if isinstance(url_value, str) and url_value.strip():
        sanitized["url"] = url_value.strip()

    excerpt_value = pointer.get("excerpt")
    if isinstance(excerpt_value, str) and excerpt_value.strip():
        sanitized["excerpt"] = excerpt_value.strip()

    if sanitized["kind"] == "transcript":
        start_ms = pointer.get("startMs")
        end_ms = pointer.get("endMs")
        if isinstance(start_ms, int) and start_ms >= 0:
            sanitized["startMs"] = start_ms
        if isinstance(end_ms, int) and end_ms >= 0:
            sanitized["endMs"] = end_ms

    return sanitized


def _human_review_day_from_raw(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    day_index = value.get("dayIndex")
    if isinstance(day_index, bool) or not isinstance(day_index, int):
        return None
    if day_index < 1 or day_index > 5:
        return None

    status_value = value.get("status")
    if not isinstance(status_value, str) or status_value != "human_review_required":
        return None

    reason_value = value.get("reason")
    if not isinstance(reason_value, str) or not reason_value.strip():
        return None

    return {
        "dayIndex": day_index,
        "score": None,
        "rubricBreakdown": {},
        "evidence": [],
        "status": status_value,
        "reason": reason_value.strip(),
    }


def _compose_day_scores(
    run: EvaluationRun, persisted_report: Mapping[str, Any]
) -> list[dict[str, Any]]:
    rows = sorted(run.day_scores, key=lambda row: row.day_index)
    scored_by_day: dict[int, dict[str, Any]] = {}
    for row in rows:
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

    persisted_day_scores = persisted_report.get("dayScores")
    placeholder_days: dict[int, dict[str, Any]] = {}
    if isinstance(persisted_day_scores, list):
        for raw_day_score in persisted_day_scores:
            placeholder = _human_review_day_from_raw(raw_day_score)
            if placeholder is None:
                continue
            day_index = int(placeholder["dayIndex"])
            if day_index in scored_by_day:
                continue
            placeholder_days[day_index] = placeholder

    payload: list[dict[str, Any]] = []
    for day_index in sorted(set(scored_by_day) | set(placeholder_days)):
        if day_index in scored_by_day:
            payload.append(scored_by_day[day_index])
            continue
        payload.append(placeholder_days[day_index])
    return payload


def compose_report(run: EvaluationRun) -> dict[str, Any]:
    persisted_report = (
        dict(run.raw_report_json) if isinstance(run.raw_report_json, Mapping) else {}
    )

    day_scores = _compose_day_scores(run, persisted_report)
    scored_days = [
        day for day in day_scores if day.get("status") != "human_review_required"
    ]
    overall_fit_score = _normalize_unit_interval(run.overall_fit_score)
    if overall_fit_score is None:
        report_score = _normalize_unit_interval(persisted_report.get("overallFitScore"))
        if report_score is not None:
            overall_fit_score = report_score
        elif scored_days:
            overall_fit_score = round(
                mean(
                    float(day["score"])
                    for day in scored_days
                    if day.get("score") is not None
                ),
                4,
            )
        else:
            overall_fit_score = 0.0

    confidence = _normalize_unit_interval(run.confidence)
    if confidence is None:
        confidence = _normalize_unit_interval(persisted_report.get("confidence"))
        if confidence is None:
            confidence = 0.0

    recommendation = run.recommendation or persisted_report.get("recommendation")

    report: dict[str, Any] = {
        "overallFitScore": overall_fit_score,
        "recommendation": _normalize_recommendation(recommendation),
        "confidence": confidence,
        "dayScores": day_scores,
        "version": {
            "model": run.model_name,
            "modelVersion": run.model_version,
            "promptVersion": run.prompt_version,
            "rubricVersion": run.rubric_version,
        },
    }

    metadata_json = run.metadata_json if isinstance(run.metadata_json, Mapping) else {}
    disabled_day_indexes = metadata_json.get("disabledDayIndexes")
    disabled_indexes: set[int] = set()
    if isinstance(disabled_day_indexes, list):
        disabled_indexes.update(
            int(value)
            for value in disabled_day_indexes
            if isinstance(value, int) and 1 <= value <= 5
        )

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
    generated_at = _normalize_datetime(
        run.generated_at or run.completed_at or run.started_at
    )
    return {
        "status": "ready",
        "generatedAt": generated_at,
        "report": compose_report(run),
    }


__all__ = ["build_ready_payload", "compose_report"]
