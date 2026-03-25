from __future__ import annotations

from types import SimpleNamespace

from app.evaluations.services.evaluations_services_evaluations_fit_profile_access_service import (
    CandidateSessionEvaluationContext,
)


def build_context(
    *, candidate_session_id: int = 101, company_id: int = 202
) -> CandidateSessionEvaluationContext:
    return CandidateSessionEvaluationContext(
        candidate_session=SimpleNamespace(id=candidate_session_id),  # type: ignore[arg-type]
        simulation=SimpleNamespace(company_id=company_id),  # type: ignore[arg-type]
        scenario_version=None,  # type: ignore[arg-type]
    )
