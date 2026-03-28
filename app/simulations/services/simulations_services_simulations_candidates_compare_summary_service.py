"""Application module for simulations services simulations candidates compare summary service workflows."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import User
from app.simulations.services.simulations_services_simulations_candidates_compare_access_service import (
    require_simulation_compare_access,
)
from app.simulations.services.simulations_services_simulations_candidates_compare_day_completion_service import (
    load_day_completion,
)
from app.simulations.services.simulations_services_simulations_candidates_compare_formatting_service import (
    display_name,
    normalize_recommendation,
    normalize_score,
)
from app.simulations.services.simulations_services_simulations_candidates_compare_model import (
    SimulationCompareAccessContext,
)
from app.simulations.services.simulations_services_simulations_candidates_compare_queries_service import (
    fetch_candidate_compare_rows,
)
from app.simulations.services.simulations_services_simulations_candidates_compare_status_service import (
    derive_candidate_compare_status,
    derive_fit_profile_status,
)
from app.simulations.services.simulations_services_simulations_candidates_compare_time_service import (
    candidate_session_created_at,
    candidate_session_updated_at,
    default_day_completion,
    fit_profile_updated_at,
)

RequireAccess = Callable[..., Awaitable[SimulationCompareAccessContext]]
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
    fit_status = derive_fit_profile_status(
        has_ready_profile=(
            row.latest_success_candidate_session_id is not None
            or row.fit_profile_generated_at is not None
        ),
        latest_run_status=row.latest_run_status,
        has_active_job=row.active_job_updated_at is not None,
    )
    candidate_status = derive_candidate_compare_status(
        fit_profile_status=fit_status,
        day_completion=day_completion,
        candidate_session_status=row.candidate_session_status,
        started_at=row.started_at,
        completed_at=row.completed_at,
    )
    resolved_name = display_name(row.candidate_name, position=index)
    updated_at = (
        fit_profile_updated_at(row)
        or candidate_session_updated_at(row, latest_submission_at=latest_submission_at)
        or candidate_session_created_at(row)
        or datetime.now(UTC).replace(microsecond=0)
    )
    return {
        "candidateSessionId": int(row.candidate_session_id),
        "candidateName": resolved_name,
        "candidateDisplayName": resolved_name,
        "status": candidate_status,
        "fitProfileStatus": fit_status,
        "overallFitScore": normalize_score(row.overall_fit_score),
        "recommendation": normalize_recommendation(row.recommendation),
        "dayCompletion": day_completion,
        "updatedAt": updated_at,
    }


async def list_candidates_compare_summary(
    db: AsyncSession,
    *,
    simulation_id: int,
    user: User,
    require_access: RequireAccess = require_simulation_compare_access,
    load_day_completion_for_sessions: LoadDayCompletion = load_day_completion,
) -> dict[str, Any]:
    """Return candidates compare summary."""
    access = await require_access(db, simulation_id=simulation_id, user=user)
    rows = await fetch_candidate_compare_rows(db, simulation_id=simulation_id)
    session_ids = [int(row.candidate_session_id) for row in rows]
    (
        day_completion_by_session,
        latest_submission_by_session,
    ) = await load_day_completion_for_sessions(
        db,
        simulation_id=simulation_id,
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
    return {"simulationId": access.simulation_id, "candidates": candidates}


__all__ = ["list_candidates_compare_summary"]
