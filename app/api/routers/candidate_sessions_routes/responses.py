from app.api.routers.candidate_sessions_routes.time_utils import utcnow
from app.domains.candidate_sessions.schemas import (
    CandidateSessionResolveResponse,
    CandidateSessionScheduleResponse,
    CandidateSimulationSummary,
    CurrentTaskResponse,
    ProgressSummary,
)
from app.domains.tasks.schemas_public import TaskPublic
from app.services.candidate_sessions.schedule_fields import (
    schedule_payload_for_candidate_session,
)


def render_claim_response(cs) -> CandidateSessionResolveResponse:
    sim = cs.simulation
    schedule_payload = schedule_payload_for_candidate_session(cs, now_utc=utcnow())
    return CandidateSessionResolveResponse(
        candidateSessionId=cs.id,
        status=cs.status,
        claimedAt=cs.claimed_at,
        startedAt=cs.started_at,
        completedAt=cs.completed_at,
        candidateName=cs.candidate_name,
        simulation=CandidateSimulationSummary(
            id=sim.id, title=sim.title, role=sim.role
        ),
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
    cs, current_task, completed_ids, completed, total, is_complete
):
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
            )
        ),
        completedTaskIds=sorted(completed_ids),
        progress=ProgressSummary(completed=completed, total=total),
        isComplete=is_complete,
    )
