"""Application module for trials services trials candidates compare summary service workflows."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import User
from app.trials.services.trials_services_trials_candidates_compare_access_service import (
    require_trial_compare_access,
)
from app.trials.services.trials_services_trials_candidates_compare_day_completion_service import (
    load_day_completion,
)
from app.trials.services.trials_services_trials_candidates_compare_formatting_service import (
    display_name,
    normalize_recommendation,
    normalize_score,
)
from app.trials.services.trials_services_trials_candidates_compare_model import (
    TrialCompareAccessContext,
)
from app.trials.services.trials_services_trials_candidates_compare_queries_service import (
    fetch_candidate_compare_rows,
)
from app.trials.services.trials_services_trials_candidates_compare_status_service import (
    derive_candidate_compare_status,
    derive_winoe_report_status,
)
from app.trials.services.trials_services_trials_candidates_compare_time_service import (
    candidate_session_created_at,
    candidate_session_updated_at,
    default_day_completion,
    winoe_report_updated_at,
)

RequireAccess = Callable[..., Awaitable[TrialCompareAccessContext]]
LoadDayCompletion = Callable[
    ..., Awaitable[tuple[dict[int, dict[str, bool]], dict[int, datetime | None]]]
]


def _build_candidate_summary(
    *,
    row: Any,
    index: int,
    day_completion: dict[str, bool],
    latest_submission_at: datetime | None,
) -> dict[str, Any]:
    winoe_report_status = derive_winoe_report_status(
        has_ready_profile=(
            row.latest_success_candidate_session_id is not None
            or row.winoe_report_generated_at is not None
        ),
        latest_run_status=row.latest_run_status,
        has_active_job=row.active_job_updated_at is not None,
    )
    candidate_status = derive_candidate_compare_status(
        winoe_report_status=winoe_report_status,
        day_completion=day_completion,
        candidate_session_status=row.candidate_session_status,
        started_at=row.started_at,
        completed_at=row.completed_at,
    )
    resolved_name = display_name(row.candidate_name, position=index)
    updated_at = (
        winoe_report_updated_at(row)
        or candidate_session_updated_at(row, latest_submission_at=latest_submission_at)
        or candidate_session_created_at(row)
        or datetime.now(UTC).replace(microsecond=0)
    )
    return {
        "candidateSessionId": int(row.candidate_session_id),
        "candidateName": resolved_name,
        "candidateDisplayName": resolved_name,
        "status": candidate_status,
        "winoeReportStatus": winoe_report_status,
        "overallWinoeScore": normalize_score(row.overall_winoe_score),
        "recommendation": normalize_recommendation(row.recommendation),
        "dayCompletion": day_completion,
        "updatedAt": updated_at,
    }


async def list_candidates_compare_summary(
    db: AsyncSession,
    *,
    trial_id: int,
    user: User,
    require_access: RequireAccess = require_trial_compare_access,
    load_day_completion_for_sessions: LoadDayCompletion = load_day_completion,
) -> dict[str, Any]:
    """Return candidates compare summary."""
    access = await require_access(db, trial_id=trial_id, user=user)
    rows = await fetch_candidate_compare_rows(db, trial_id=trial_id)
    session_ids = [int(row.candidate_session_id) for row in rows]
    (
        day_completion_by_session,
        latest_submission_by_session,
    ) = await load_day_completion_for_sessions(
        db,
        trial_id=trial_id,
        candidate_session_ids=session_ids,
    )
    candidates = [
        _build_candidate_summary(
            row=row,
            index=index,
            day_completion=day_completion_by_session.get(
                int(row.candidate_session_id), default_day_completion()
            ),
            latest_submission_at=latest_submission_by_session.get(
                int(row.candidate_session_id)
            ),
        )
        for index, row in enumerate(rows)
    ]
    return {"trialId": access.trial_id, "candidates": candidates}


__all__ = ["list_candidates_compare_summary"]
