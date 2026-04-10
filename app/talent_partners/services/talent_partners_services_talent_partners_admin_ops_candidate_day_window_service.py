"""Application module for Talent Partners services Talent Partners admin ops candidate day window service workflows."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.services import (
    candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_service as day_close_jobs_service,
)
from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    derive_current_day_window,
    derive_day_windows,
    parse_local_time,
    serialize_day_windows,
    validate_timezone,
)
from app.shared.utils.shared_utils_env_utils import is_local_or_test
from app.talent_partners.repositories.admin_action_audits import (
    talent_partners_repositories_admin_action_audits_talent_partners_admin_action_audits_core_repository as admin_audit_repo,
)
from app.talent_partners.services.talent_partners_services_talent_partners_admin_ops_audit_service import (
    normalize_datetime,
    sanitized_reason,
    unsafe_operation,
)
from app.talent_partners.services.talent_partners_services_talent_partners_admin_ops_candidate_helpers_service import (
    apply_model_updates,
    load_candidate_session_for_update,
)
from app.talent_partners.services.talent_partners_services_talent_partners_admin_ops_types_service import (
    CANDIDATE_SESSION_DAY_WINDOW_CONTROL_ACTION,
    CandidateSessionDayWindowControlResult,
)

_MINUTE = timedelta(minutes=1)


def _floor_to_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def _ceil_to_minute(value: datetime) -> datetime:
    if value.second or value.microsecond:
        value = value + _MINUTE
    return value.replace(second=0, microsecond=0)


def _resolve_relative_window_times(
    *,
    now_local: datetime,
    minutes_already_open: int,
    minutes_until_cutoff: int,
) -> tuple[time, time]:
    day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = now_local.replace(hour=23, minute=59, second=0, microsecond=0)
    start_dt = _floor_to_minute(
        max(day_start, now_local - timedelta(minutes=minutes_already_open))
    )
    end_dt = _ceil_to_minute(
        min(day_end, now_local + timedelta(minutes=minutes_until_cutoff))
    )
    if end_dt > day_end:
        end_dt = day_end
    if end_dt <= start_dt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to derive an active local day window from the requested cutoff settings.",
        )
    return start_dt.timetz().replace(tzinfo=None), end_dt.timetz().replace(tzinfo=None)


def _resolve_window_times(
    *,
    now_local: datetime,
    minutes_already_open: int,
    minutes_until_cutoff: int,
    window_start_local: str | None,
    window_end_local: str | None,
) -> tuple[time, time]:
    if window_start_local is None and window_end_local is None:
        return _resolve_relative_window_times(
            now_local=now_local,
            minutes_already_open=minutes_already_open,
            minutes_until_cutoff=minutes_until_cutoff,
        )
    if window_start_local is None or window_end_local is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="windowStartLocal and windowEndLocal must be provided together.",
        )
    start_local = parse_local_time(window_start_local)
    end_local = parse_local_time(window_end_local)
    if end_local <= start_local:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="windowEndLocal must be after windowStartLocal.",
        )
    return start_local, end_local


def _day1_local_date(*, target_day_index: int, local_today: date) -> date:
    return local_today - timedelta(days=target_day_index - 1)


async def set_candidate_session_day_window(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    target_day_index: int,
    reason: str,
    candidate_timezone: str | None,
    minutes_already_open: int,
    minutes_until_cutoff: int,
    window_start_local: str | None,
    window_end_local: str | None,
    dry_run: bool,
    now: datetime | None = None,
) -> CandidateSessionDayWindowControlResult:
    """Retarget a candidate session day window for local/test validation."""
    if not is_local_or_test():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    resolved_now = normalize_datetime(now) or datetime.now(UTC)
    candidate_session = await load_candidate_session_for_update(
        db, candidate_session_id
    )
    if not (candidate_session.candidate_auth0_sub or "").strip():
        unsafe_operation(
            "Candidate session must be claimed before day-window controls can be used.",
            details={"candidateSessionId": candidate_session_id},
        )

    existing_timezone = (
        getattr(candidate_session, "candidate_timezone", None) or ""
    ).strip()
    timezone_value = (candidate_timezone or existing_timezone).strip()
    if not timezone_value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="candidateTimezone is required when the session is not yet scheduled.",
        )
    normalized_timezone = validate_timezone(timezone_value)
    local_now = resolved_now.astimezone(ZoneInfo(normalized_timezone))
    resolved_window_start, resolved_window_end = _resolve_window_times(
        now_local=local_now,
        minutes_already_open=minutes_already_open,
        minutes_until_cutoff=minutes_until_cutoff,
        window_start_local=window_start_local,
        window_end_local=window_end_local,
    )
    scheduled_start_local = datetime.combine(
        _day1_local_date(
            target_day_index=target_day_index, local_today=local_now.date()
        ),
        resolved_window_start,
        tzinfo=ZoneInfo(normalized_timezone),
    )
    scheduled_start_at = scheduled_start_local.astimezone(UTC)
    day_windows = derive_day_windows(
        scheduled_start_at_utc=scheduled_start_at,
        candidate_tz=normalized_timezone,
        day_window_start_local=resolved_window_start,
        day_window_end_local=resolved_window_end,
        overrides=None,
        overrides_enabled=False,
        total_days=5,
    )
    serialized_day_windows = serialize_day_windows(day_windows)
    current_day_window = derive_current_day_window(
        day_windows,
        now_utc=resolved_now,
    )
    resolved_schedule_locked_at = (
        normalize_datetime(getattr(candidate_session, "schedule_locked_at", None))
        or resolved_now
    )
    updates = {
        "status": "in_progress",
        "started_at": normalize_datetime(getattr(candidate_session, "started_at", None))
        or resolved_now,
        "completed_at": None,
        "scheduled_start_at": scheduled_start_at,
        "candidate_timezone": normalized_timezone,
        "day_windows_json": serialized_day_windows,
        "schedule_locked_at": resolved_schedule_locked_at,
    }
    changed_fields = apply_model_updates(candidate_session, updates)
    await day_close_jobs_service.enqueue_day_close_jobs(
        db,
        candidate_session=candidate_session,
        commit=False,
    )

    if dry_run:
        await db.rollback()
        return CandidateSessionDayWindowControlResult(
            candidate_session_id=candidate_session_id,
            candidate_status="in_progress",
            status="dry_run",
            target_day_index=target_day_index,
            candidate_timezone=normalized_timezone,
            scheduled_start_at=scheduled_start_at,
            schedule_locked_at=resolved_schedule_locked_at,
            day_windows=serialized_day_windows,
            current_day_window=current_day_window,
            audit_id=None,
        )

    audit = await admin_audit_repo.create_audit(
        db,
        actor_type="admin_api_key",
        actor_id="local_admin_key",
        action=CANDIDATE_SESSION_DAY_WINDOW_CONTROL_ACTION,
        target_type="candidate_session",
        target_id=candidate_session_id,
        payload_json={
            "reason": sanitized_reason(reason),
            "targetDayIndex": target_day_index,
            "candidateTimezone": normalized_timezone,
            "windowStartLocal": resolved_window_start.strftime("%H:%M"),
            "windowEndLocal": resolved_window_end.strftime("%H:%M"),
            "minutesAlreadyOpen": minutes_already_open,
            "minutesUntilCutoff": minutes_until_cutoff,
            "noOp": not changed_fields,
            "changedFields": changed_fields,
        },
        commit=False,
    )
    await db.commit()
    return CandidateSessionDayWindowControlResult(
        candidate_session_id=candidate_session_id,
        candidate_status="in_progress",
        status="ok",
        target_day_index=target_day_index,
        candidate_timezone=normalized_timezone,
        scheduled_start_at=scheduled_start_at,
        schedule_locked_at=resolved_schedule_locked_at,
        day_windows=serialized_day_windows,
        current_day_window=current_day_window,
        audit_id=audit.id,
    )


__all__ = ["set_candidate_session_day_window"]
