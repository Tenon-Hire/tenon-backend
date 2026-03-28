"""Application module for jobs handlers day close enforcement handler workflows."""

from __future__ import annotations

import logging
from typing import Any

from app.candidates.candidate_sessions.repositories import repository as cs_repo
from app.candidates.candidate_sessions.services.candidates_candidate_sessions_services_candidates_candidate_sessions_day_close_jobs_service import (
    DAY_CLOSE_ENFORCEMENT_JOB_TYPE,
)
from app.shared.database import async_session_maker
from app.shared.http.dependencies.shared_http_dependencies_github_native_utils import (
    get_github_client,
)
from app.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_helpers_handler import (
    _extract_head_sha,
    _parse_optional_datetime,
    _parse_positive_int,
    _resolve_default_branch,
    _to_iso_z,
)
from app.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_helpers_handler import (
    _revoke_repo_write_access as _revoke_repo_write_access_impl,
)
from app.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_runtime_handler import (
    handle_day_close_enforcement_impl,
)
from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)

logger = logging.getLogger(__name__)


async def _revoke_repo_write_access(github_client, **kwargs) -> str:
    return await _revoke_repo_write_access_impl(github_client, logger=logger, **kwargs)


async def handle_day_close_enforcement(payload_json: dict[str, Any]) -> dict[str, Any]:
    """Handle day close enforcement."""
    return await handle_day_close_enforcement_impl(
        payload_json,
        parse_positive_int=_parse_positive_int,
        parse_optional_datetime=_parse_optional_datetime,
        to_iso_z=_to_iso_z,
        extract_head_sha=_extract_head_sha,
        resolve_default_branch=_resolve_default_branch,
        revoke_repo_write_access=_revoke_repo_write_access,
        async_session_maker=async_session_maker,
        get_github_client=get_github_client,
        cs_repo=cs_repo,
        workspace_repo=workspace_repo,
        logger=logger,
    )


__all__ = ["DAY_CLOSE_ENFORCEMENT_JOB_TYPE", "handle_day_close_enforcement"]
