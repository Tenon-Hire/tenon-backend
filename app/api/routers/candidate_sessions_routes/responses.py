from datetime import UTC, datetime

from app.api.routers.candidate_sessions_routes.time_utils import utcnow
from app.domains.candidate_sessions import service as cs_service
from app.domains.candidate_sessions.schemas import (
    CandidateSessionResolveResponse,
    CandidateSessionScheduleResponse,
    CandidateSimulationSummary,
    CurrentTaskResponse,
    CurrentTaskWindow,
    ProgressSummary,
)
from app.domains.simulations.schemas import resolve_simulation_ai_fields
from app.domains.tasks.schemas_public import TaskPublic
from app.services.candidate_sessions.schedule_fields import (
    schedule_payload_for_candidate_session,
)


def _resolve_cutoff_fields(day_audit) -> tuple[str | None, datetime | None]:
    if day_audit is None:
        return None, None

    cutoff_commit_sha = getattr(day_audit, "cutoff_commit_sha", None)
    cutoff_at = getattr(day_audit, "cutoff_at", None)
    if isinstance(cutoff_at, datetime) and cutoff_at.tzinfo is None:
        cutoff_at = cutoff_at.replace(tzinfo=UTC)
    return cutoff_commit_sha, cutoff_at


def _resolve_simulation_summary(
    cs, *, include_content_sections: bool
) -> CandidateSimulationSummary:
    sim = cs.simulation
    summary = CandidateSimulationSummary(id=sim.id, title=sim.title, role=sim.role)
    if include_content_sections:
        # Extend here if resolve response later carries start-gated content blocks.
        return summary
    # Resolve response intentionally stays minimal pre-start.
    return summary


def render_claim_response(cs) -> CandidateSessionResolveResponse:
    now_utc = utcnow()
    schedule_payload = schedule_payload_for_candidate_session(cs, now_utc=now_utc)
    window_start_at, window_end_at = cs_service.compute_day1_window(cs)
    include_content_sections = cs_service.is_schedule_started_for_content(
        cs, now=now_utc
    )
    (
        ai_notice_version,
        ai_notice_text,
        eval_enabled_by_day,
    ) = resolve_simulation_ai_fields(
        notice_version=getattr(cs.simulation, "ai_notice_version", None),
        notice_text=getattr(cs.simulation, "ai_notice_text", None),
        eval_enabled_by_day=getattr(
            cs.simulation,
            "ai_eval_enabled_by_day",
            None,
        ),
    )
    return CandidateSessionResolveResponse(
        candidateSessionId=cs.id,
        status=cs.status,
        claimedAt=cs.claimed_at,
        startedAt=cs.started_at,
        completedAt=cs.completed_at,
        candidateName=cs.candidate_name,
        simulation=_resolve_simulation_summary(
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


def render_schedule_response(cs) -> CandidateSessionScheduleResponse:
    schedule_payload = schedule_payload_for_candidate_session(cs, now_utc=utcnow())
    return CandidateSessionScheduleResponse(
        candidateSessionId=cs.id,
        scheduledStartAt=schedule_payload["scheduledStartAt"],
        candidateTimezone=schedule_payload["candidateTimezone"],
        dayWindows=schedule_payload["dayWindows"],
        scheduleLockedAt=schedule_payload["scheduleLockedAt"],
    )


def build_current_task_response(
    cs,
    current_task,
    completed_ids,
    completed,
    total,
    is_complete,
    *,
    day_audit=None,
    now_utc,
):
    current_window = None
    if not is_complete and current_task is not None:
        task_window = cs_service.compute_task_window(cs, current_task, now_utc=now_utc)
        if (
            task_window.window_start_at is not None
            and task_window.window_end_at is not None
        ):
            current_window = CurrentTaskWindow(
                windowStartAt=task_window.window_start_at,
                windowEndAt=task_window.window_end_at,
                nextOpenAt=task_window.next_open_at,
                isOpen=task_window.is_open,
                now=task_window.now,
            )

    cutoff_commit_sha, cutoff_at = _resolve_cutoff_fields(day_audit)

    return CurrentTaskResponse(
        candidateSessionId=cs.id,
        status=cs.status,
        currentDayIndex=None if is_complete else current_task.day_index,
        currentTask=(
            None
            if is_complete
            else TaskPublic(
                id=current_task.id,
                dayIndex=current_task.day_index,
                title=current_task.title,
                type=current_task.type,
                description=current_task.description,
                cutoffCommitSha=cutoff_commit_sha,
                cutoffAt=cutoff_at,
            )
        ),
        completedTaskIds=sorted(completed_ids),
        progress=ProgressSummary(completed=completed, total=total),
        isComplete=is_complete,
        currentWindow=current_window,
    )
