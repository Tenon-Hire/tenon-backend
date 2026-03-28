"""Application module for evaluations services evaluations evaluator evidence service workflows."""

from __future__ import annotations

from typing import Any

from app.evaluations.services.evaluations_services_evaluations_evaluator_evidence_code_service import (
    _build_code_day_evidence,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_evidence_text_service import (
    _build_text_day_evidence,
    _fallback_evidence,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_evidence_transcript_service import (
    _build_transcript_day_evidence,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_models_service import (
    DayEvaluationInput,
)


def _build_day_evidence(day: DayEvaluationInput) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    if day.day_index in {1, 5}:
        evidence = _build_text_day_evidence(day)
    elif day.day_index in {2, 3}:
        evidence = _build_code_day_evidence(day)
    elif day.day_index == 4:
        evidence = _build_transcript_day_evidence(day)
    return evidence or _fallback_evidence(day)


__all__ = ["_build_day_evidence"]
