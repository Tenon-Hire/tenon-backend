"""Application module for evaluations services reviewer report composer workflows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.evaluations.repositories.evaluations_repositories_evaluations_core_model import (
    EvaluationRun,
)

from .evaluations_services_evaluations_winoe_report_composer_evidence_service import (
    _sanitize_evidence,
)

_LEGACY_REVIEWER_KEY_MAP = {
    "day1": "designDocReviewer",
    "day23": "codeImplementationReviewer",
    "day4": "demoPresentationReviewer",
    "day5": "reflectionEssayReviewer",
}


def _normalize_reviewer_agent_key(value: object) -> str:
    if isinstance(value, str):
        stripped = value.strip()
        return _LEGACY_REVIEWER_KEY_MAP.get(stripped, stripped)
    return ""


def _compose_reviewer_reports(run: EvaluationRun) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    reviewer_rows = getattr(run, "reviewer_reports", None) or []
    for row in sorted(
        reviewer_rows,
        key=lambda value: (value.day_index, value.reviewer_agent_key, value.id),
    ):
        evidence = [
            sanitized
            for sanitized in (
                _sanitize_evidence(pointer)
                for pointer in (row.evidence_citations_json or [])
            )
            if sanitized is not None
        ]
        payload.append(
            {
                "reviewerAgentKey": _normalize_reviewer_agent_key(
                    row.reviewer_agent_key
                ),
                "dayIndex": int(row.day_index),
                "submissionKind": row.submission_kind,
                "score": float(row.score),
                "dimensionalScores": dict(row.dimensional_scores_json or {}),
                "evidenceCitations": evidence,
                "assessment": row.assessment_text,
                "strengths": list(row.strengths_json or []),
                "concerns": list(row.risks_json or []),
            }
        )

    persisted_report = (
        run.raw_report_json if isinstance(run.raw_report_json, Mapping) else {}
    )
    persisted_reviewer_reports = persisted_report.get("reviewerReports")
    if isinstance(persisted_reviewer_reports, list) and not payload:
        for raw_report in persisted_reviewer_reports:
            if not isinstance(raw_report, Mapping):
                continue
            evidence = [
                sanitized
                for sanitized in (
                    _sanitize_evidence(pointer)
                    for pointer in raw_report.get("evidenceCitations", [])
                )
                if sanitized is not None
            ]
            payload.append(
                {
                    "reviewerAgentKey": _normalize_reviewer_agent_key(
                        raw_report.get("reviewerAgentKey")
                    ),
                    "dayIndex": int(raw_report.get("dayIndex") or 0),
                    "submissionKind": str(raw_report.get("submissionKind") or ""),
                    "score": float(raw_report.get("score") or 0.0),
                    "dimensionalScores": dict(
                        raw_report.get("dimensionalScores") or {}
                    ),
                    "evidenceCitations": evidence,
                    "assessment": str(raw_report.get("assessment") or ""),
                    "strengths": [
                        str(item)
                        for item in (raw_report.get("strengths") or [])
                        if isinstance(item, str)
                    ],
                    "concerns": [
                        str(item)
                        for item in (raw_report.get("concerns") or [])
                        if isinstance(item, str)
                    ],
                }
            )
    return payload


__all__ = ["_compose_reviewer_reports"]
