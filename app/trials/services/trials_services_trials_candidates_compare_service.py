"""Application module for trials services trials candidates compare service workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import User
from app.trials.services.trials_services_trials_candidates_compare_access_service import (
    require_trial_compare_access,
)
from app.trials.services.trials_services_trials_candidates_compare_day_completion_service import (
    load_day_completion as _load_day_completion_impl,
)
from app.trials.services.trials_services_trials_candidates_compare_formatting_service import (
    anonymized_candidate_label as _anonymized_candidate_label,
)
from app.trials.services.trials_services_trials_candidates_compare_formatting_service import (
    normalize_recommendation as _normalize_recommendation,
)
from app.trials.services.trials_services_trials_candidates_compare_formatting_service import (
    normalize_score as _normalize_score,
)
from app.trials.services.trials_services_trials_candidates_compare_model import (
    TrialCompareAccessContext,
)
from app.trials.services.trials_services_trials_candidates_compare_status_service import (
    derive_candidate_compare_status,
    derive_winoe_report_status,
)
from app.trials.services.trials_services_trials_candidates_compare_summary_service import (
    list_candidates_compare_summary as _list_candidates_compare_summary_impl,
)
from app.trials.services.trials_services_trials_candidates_compare_time_service import (
    candidate_session_created_at as _candidate_session_created_at,
)
from app.trials.services.trials_services_trials_candidates_compare_time_service import (
    candidate_session_updated_at as _candidate_session_updated_at,
)
from app.trials.services.trials_services_trials_candidates_compare_time_service import (
    max_datetime as _max_datetime,
)
from app.trials.services.trials_services_trials_candidates_compare_time_service import (
    winoe_report_updated_at as _winoe_report_updated_at,
)


async def _load_day_completion(
    db: AsyncSession,
    *,
    trial_id: int,
    candidate_session_ids: list[int],
):
    return await _load_day_completion_impl(
        db,
        trial_id=trial_id,
        candidate_session_ids=candidate_session_ids,
    )


async def list_candidates_compare_summary(
    db: AsyncSession,
    *,
    trial_id: int,
    user: User,
):
    """Return candidates compare summary."""
    return await _list_candidates_compare_summary_impl(
        db,
        trial_id=trial_id,
        user=user,
        require_access=require_trial_compare_access,
        load_day_completion_for_sessions=_load_day_completion,
    )


__all__ = [
    "TrialCompareAccessContext",
    "_anonymized_candidate_label",
    "_candidate_session_created_at",
    "_candidate_session_updated_at",
    "_winoe_report_updated_at",
    "_max_datetime",
    "_normalize_recommendation",
    "_normalize_score",
    "derive_candidate_compare_status",
    "derive_winoe_report_status",
    "list_candidates_compare_summary",
    "require_trial_compare_access",
]
