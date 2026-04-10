"""Application module for candidates routes candidate sessions routes candidates candidate sessions routes responses routes workflows."""

from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_schedule_fields_service import (
    schedule_payload_for_candidate_session,
)
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_responses_claim_routes import (
    render_claim_response as _render_claim_response,
)
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_responses_current_task_routes import (
    build_current_task_response,
)
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_time_utils import (
    utcnow,
)
from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CandidateSessionResolveResponse,
    CandidateSessionScheduleResponse,
    CandidateTrialSummary,
)


def _resolve_trial_summary(
    cs, *, include_content_sections: bool
) -> CandidateTrialSummary:
    sim = cs.trial
    summary = CandidateTrialSummary(id=sim.id, title=sim.title, role=sim.role)
    if include_content_sections:
        return summary
    return summary


def render_claim_response(cs) -> CandidateSessionResolveResponse:
    """Render claim response."""
    return _render_claim_response(cs, resolve_trial_summary=_resolve_trial_summary)


def render_schedule_response(cs) -> CandidateSessionScheduleResponse:
    """Render schedule response."""
    schedule_payload = schedule_payload_for_candidate_session(cs, now_utc=utcnow())
    return CandidateSessionScheduleResponse(
        candidateSessionId=cs.id,
        scheduledStartAt=schedule_payload["scheduledStartAt"],
        candidateTimezone=schedule_payload["candidateTimezone"],
        dayWindows=schedule_payload["dayWindows"],
        scheduleLockedAt=schedule_payload["scheduleLockedAt"],
    )


__all__ = [
    "_resolve_trial_summary",
    "build_current_task_response",
    "render_claim_response",
    "render_schedule_response",
]
