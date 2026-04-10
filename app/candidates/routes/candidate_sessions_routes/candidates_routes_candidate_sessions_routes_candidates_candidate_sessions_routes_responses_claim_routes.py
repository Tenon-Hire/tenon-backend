"""Build response payloads for candidate-session claim and resolve endpoints."""

from __future__ import annotations

from app.ai import require_candidate_settings_from_snapshot
from app.candidates.candidate_sessions import services as cs_service
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_schedule_fields_service import (
    schedule_payload_for_candidate_session,
)
from app.candidates.routes.candidate_sessions_routes.candidates_routes_candidate_sessions_routes_candidates_candidate_sessions_routes_time_utils import (
    utcnow,
)
from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CandidateSessionResolveResponse,
)


def render_claim_response(
    cs, *, resolve_trial_summary
) -> CandidateSessionResolveResponse:
    """Project session state into the public claim response schema."""
    now_utc = utcnow()
    schedule_payload = schedule_payload_for_candidate_session(cs, now_utc=now_utc)
    window_start_at, window_end_at = cs_service.compute_day1_window(cs)
    include_content_sections = cs_service.is_schedule_started_for_content(
        cs, now=now_utc
    )
    scenario_version = getattr(cs, "__dict__", {}).get("scenario_version")
    (
        ai_notice_version,
        ai_notice_text,
        eval_enabled_by_day,
    ) = require_candidate_settings_from_snapshot(
        getattr(scenario_version, "ai_policy_snapshot_json", None),
        scenario_version_id=getattr(cs, "scenario_version_id", None),
    )
    return CandidateSessionResolveResponse(
        candidateSessionId=cs.id,
        status=cs.status,
        claimedAt=cs.claimed_at,
        startedAt=cs.started_at,
        completedAt=cs.completed_at,
        candidateName=cs.candidate_name,
        trial=resolve_trial_summary(
            cs, include_content_sections=include_content_sections
        ),
        aiNoticeText=ai_notice_text,
        aiNoticeVersion=ai_notice_version,
        evalEnabledByDay=eval_enabled_by_day,
        startAt=schedule_payload["scheduledStartAt"],
        windowStartAt=window_start_at,
        windowEndAt=window_end_at,
        scheduledStartAt=schedule_payload["scheduledStartAt"],
        candidateTimezone=schedule_payload["candidateTimezone"],
        dayWindows=schedule_payload["dayWindows"],
        scheduleLockedAt=schedule_payload["scheduleLockedAt"],
        currentDayWindow=schedule_payload["currentDayWindow"],
    )
