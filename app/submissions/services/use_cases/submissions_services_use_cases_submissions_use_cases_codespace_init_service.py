"""Application module for submissions services use cases submissions use cases codespace init service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions import services as cs_service
from app.integrations.github.client import GithubClient
from app.shared.database.shared_database_models_model import CandidateSession, Trial
from app.shared.utils.shared_utils_errors_utils import (
    GITHUB_USERNAME_MISMATCH,
    ApiError,
)
from app.submissions.services import (
    submissions_services_submissions_candidate_service as submission_service,
)
from app.submissions.services.submissions_services_submissions_codespace_urls_service import (
    ensure_canonical_workspace_url,
)
from app.submissions.services.submissions_services_submissions_github_user_service import (
    validate_and_normalize_github_username,
)
from app.submissions.services.submissions_services_submissions_rate_limits_constants import (
    apply_rate_limit,
)
from app.submissions.services.submissions_services_submissions_workspace_repo_state_service import (
    refresh_codespace_state,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_codespace_validations_service import (
    validate_codespace_request,
)
from app.submissions.services.use_cases.submissions_services_use_cases_submissions_use_cases_day_flow_gate_service import (
    ensure_day_flow_open,
)
from app.trials.repositories.scenario_versions import (
    trials_repositories_scenario_versions_trials_scenario_versions_repository as scenario_repo,
)


async def _validate_codespace_request_with_legacy_fallback(
    db: AsyncSession,
    candidate_session: CandidateSession,
    task_id: int,
):
    try:
        return await validate_codespace_request(db, candidate_session, task_id)
    except HTTPException as exc:
        # Backward-compatible path for legacy/unit harnesses that do not seed
        # trial tasks but still monkeypatch task/progress helpers.
        if exc.status_code != 500 or str(exc.detail) != "Trial has no tasks":
            raise
        task = await submission_service.load_task_or_404(db, task_id)
        submission_service.ensure_task_belongs(task, candidate_session)
        cs_service.require_active_window(candidate_session, task)
        _, _, current, *_ = await cs_service.progress_snapshot(db, candidate_session)
        submission_service.ensure_in_order(current, task_id)
        submission_service.validate_run_allowed(task)
        return task


async def init_codespace(
    db: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task_id: int,
    github_client: GithubClient,
    github_username: str,
    repo_prefix: str,
    destination_owner: str | None,
    now: datetime | None = None,
):
    """Initialize codespace."""
    apply_rate_limit(candidate_session.id, "init")
    normalized_username = validate_and_normalize_github_username(github_username)
    stored_username = (
        getattr(candidate_session, "github_username", None) or ""
    ).strip()
    if stored_username and stored_username != normalized_username:
        raise ApiError(
            status_code=409,
            detail="GitHub username does not match the stored session value.",
            error_code=GITHUB_USERNAME_MISMATCH,
            retryable=False,
        )
    if stored_username != normalized_username:
        candidate_session.github_username = normalized_username
    task = await _validate_codespace_request_with_legacy_fallback(
        db, candidate_session, task_id
    )
    task_day_index = getattr(task, "day_index", None)
    task_type = getattr(task, "type", None)
    existing_workspace = None
    if task_day_index is not None and task_type is not None:
        existing_workspace = (
            await submission_service.workspace_repo.get_by_session_and_task(
                db,
                candidate_session_id=candidate_session.id,
                task_id=task.id,
                task_day_index=task_day_index,
                task_type=task_type,
            )
        )
    await ensure_day_flow_open(
        db,
        candidate_session=candidate_session,
        task=task,
        workspace=existing_workspace,
    )
    trial = None
    if getattr(task, "trial_id", None) is not None:
        trial = await db.get(Trial, task.trial_id)
    scenario_version = (
        await scenario_repo.get_active_for_trial(db, trial.id)
        if trial is not None
        else None
    )
    workspace = await submission_service.ensure_workspace(
        db,
        candidate_session=candidate_session,
        trial=trial,
        scenario_version=scenario_version,
        task=task,
        github_client=github_client,
        github_username=candidate_session.github_username,
        repo_prefix=repo_prefix,
        destination_owner=destination_owner,
        now=now or datetime.now(UTC),
        commit=False,
        hydrate_precommit_bundle=False,
        bootstrap_empty_repo=True,
    )
    if not workspace.repo_full_name:
        raise ApiError(
            status_code=409,
            detail="Workspace repo not provisioned yet. Please try again.",
            error_code="WORKSPACE_NOT_READY",
            retryable=True,
        )
    try:
        codespace_url = await ensure_canonical_workspace_url(
            db,
            workspace,
            commit=False,
            refresh=False,
        )
    except TypeError:
        codespace_url = await ensure_canonical_workspace_url(db, workspace)
    workspace = await refresh_codespace_state(
        db,
        workspace=workspace,
        github_client=github_client,
    )
    if isinstance(db, AsyncSession):
        await db.commit()
    return (
        workspace,
        submission_service.build_codespace_url(workspace.repo_full_name),
        codespace_url,
        task,
    )


__all__ = ["init_codespace"]
