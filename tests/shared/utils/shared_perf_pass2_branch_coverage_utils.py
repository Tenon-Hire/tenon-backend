from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.candidates.candidate_sessions.services import (
    candidates_candidate_sessions_services_candidates_candidate_sessions_progress_service as cs_progress,
)
from app.media.repositories.recordings import (
    RECORDING_ASSET_STATUS_UPLOADED,
)
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.transcripts import repository as transcripts_repo
from app.notifications.services import (
    notifications_services_notifications_invite_content_service as invite_content,
)
from app.shared.jobs.repositories import repository as jobs_repo
from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from app.submissions.schemas.submissions_schemas_submissions_task_drafts_schema import (
    TaskDraftUpsertRequest,
)
from app.submissions.services import (
    submissions_services_submissions_submission_progress_service as submission_progress,
)
from app.submissions.services.use_cases import (
    submissions_services_use_cases_submissions_use_cases_codespace_init_service as codespace_init_use_case,
)
from app.submissions.services.use_cases import (
    submissions_services_use_cases_submissions_use_cases_codespace_init_service as codespace_init_with_fallback,
)
from app.submissions.services.use_cases import (
    submissions_services_use_cases_submissions_use_cases_codespace_validations_service as codespace_validations,
)
from app.submissions.services.use_cases import (
    submissions_services_use_cases_submissions_use_cases_submit_workspace_service as submit_workspace_use_case,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_codespace_init_service import (
    _validate_codespace_request_with_legacy_fallback,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_submit_workspace_service import (
    fetch_workspace_and_branch,
)
from app.tasks.routes.tasks import tasks_routes_tasks_tasks_draft_routes as draft_route
from app.tasks.routes.tasks import (
    tasks_routes_tasks_tasks_runtime_utils as task_helpers,
)
from app.trials.repositories import repository_owned
from app.trials.repositories.trials_repositories_trials_trial_model import (
    TRIAL_STATUS_TERMINATED,
)
from app.trials.routes.trials_routes import (
    lifecycle as lifecycle_route,
)
from tests.shared.factories import (
    create_candidate_session,
    create_company,
    create_talent_partner,
    create_trial,
)


def _async_return(value):
    async def _inner(*_args, **_kwargs):
        return value

    return _inner


class _RowsResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def all(self):
        return self._rows


__all__ = [name for name in globals() if not name.startswith("__")]
