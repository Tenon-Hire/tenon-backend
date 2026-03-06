from app.domains.candidate_sessions import repository as cs_repo
from app.domains.candidate_sessions.service.claims import claim_invite_with_principal
from app.domains.candidate_sessions.service.email import (
    normalize_email as _normalize_email,
)
from app.domains.candidate_sessions.service.fetch import (
    fetch_by_token,
    fetch_by_token_for_update,
    fetch_owned_session,
)
from app.domains.candidate_sessions.service.invites import invite_list_for_principal
from app.domains.candidate_sessions.service.ownership import (
    ensure_candidate_ownership as _ensure_candidate_ownership,
)
from app.domains.candidate_sessions.service.progress import (
    completed_task_ids,
    load_tasks,
    progress_snapshot,
)
from app.domains.candidate_sessions.service.schedule import (
    schedule_candidate_session,
)
from app.domains.candidate_sessions.service.status import (
    mark_in_progress,
    require_not_expired,
)
from app.services.candidate_sessions.day_close_jobs import (
    DAY_CLOSE_FINALIZE_TEXT_DAY_INDEXES,
    DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE,
    build_day_close_finalize_text_payload,
    day_close_finalize_text_idempotency_key,
    enqueue_day_close_finalize_text_jobs,
)
from app.services.candidate_sessions.schedule_gates import (
    TaskWindow,
    build_schedule_not_started_error,
    build_task_window_closed_error,
    compute_day1_window,
    compute_task_window,
    ensure_schedule_started_for_content,
    is_schedule_started_for_content,
    require_active_window,
)

__all__ = [
    "cs_repo",
    "claim_invite_with_principal",
    "completed_task_ids",
    "fetch_by_token",
    "fetch_by_token_for_update",
    "fetch_owned_session",
    "invite_list_for_principal",
    "load_tasks",
    "mark_in_progress",
    "progress_snapshot",
    "schedule_candidate_session",
    "DAY_CLOSE_FINALIZE_TEXT_JOB_TYPE",
    "DAY_CLOSE_FINALIZE_TEXT_DAY_INDEXES",
    "build_day_close_finalize_text_payload",
    "day_close_finalize_text_idempotency_key",
    "enqueue_day_close_finalize_text_jobs",
    "TaskWindow",
    "build_schedule_not_started_error",
    "build_task_window_closed_error",
    "compute_day1_window",
    "compute_task_window",
    "is_schedule_started_for_content",
    "ensure_schedule_started_for_content",
    "require_active_window",
    "require_not_expired",
    "_normalize_email",
    "_ensure_candidate_ownership",
]
