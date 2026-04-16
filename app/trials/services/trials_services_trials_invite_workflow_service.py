"""Application module for trials services trials invite workflow service workflows."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.github import GithubClient
from app.notifications.services import service as notification_service
from app.shared.time.shared_time_now_service import utcnow as shared_utcnow
from app.submissions.services.submissions_services_submissions_workspace_bootstrap_service import (
    build_candidate_repo_name,
)
from app.trials import services as sim_service
from app.trials.services import (
    trials_services_trials_invite_preprovision_service as invite_preprovision,
)

logger = logging.getLogger(__name__)


async def _cleanup_candidate_repo(
    github_client: GithubClient, repo_full_name: str
) -> None:
    """Delete a freshly created candidate repo best-effort."""
    try:
        await github_client.delete_repo(repo_full_name)
    except Exception as exc:  # pragma: no cover - cleanup should not mask root cause
        logger.warning(
            "candidate_repo_cleanup_failed",
            extra={"repo_full_name": repo_full_name, "error": str(exc)},
        )


async def _rollback_if_supported(db: AsyncSession) -> None:
    rollback = getattr(db, "rollback", None)
    if callable(rollback):
        await rollback()


async def create_candidate_invite_workflow(
    db: AsyncSession,
    *,
    trial_id: int,
    payload,
    user_id: int,
    email_service,
    github_client: GithubClient,
    now: datetime | None = None,
):
    """Create candidate invite workflow."""
    try:
        sim, tasks = await sim_service.require_owned_trial_with_tasks(
            db,
            trial_id,
            user_id,
            for_update=True,
        )
    except TypeError as exc:
        if "for_update" not in str(exc):
            raise
        sim, tasks = await sim_service.require_owned_trial_with_tasks(
            db,
            trial_id,
            user_id,
        )
    sim_service.require_trial_invitable(sim)
    now = now or shared_utcnow()
    try:
        scenario_version = await sim_service.lock_active_scenario_for_invites(
            db,
            trial_id=trial_id,
            now=now,
            trial=sim,
        )
    except TypeError as exc:
        if "trial" not in str(exc):
            raise
        scenario_version = await sim_service.lock_active_scenario_for_invites(
            db,
            trial_id=trial_id,
            now=now,
        )
    cs, outcome = await sim_service.create_or_resend_invite(
        db,
        trial_id,
        payload,
        scenario_version_id=scenario_version.id,
        now=now,
    )
    fresh_candidate_session = bool(getattr(cs, "_invite_newly_created", False))
    invite_url = sim_service.invite_url(cs.token)
    try:
        await invite_preprovision.preprovision_workspaces(
            db,
            cs,
            sim,
            scenario_version,
            tasks,
            github_client,
            now=now,
            fresh_candidate_session=fresh_candidate_session,
        )
        await notification_service.send_invite_email(
            db,
            candidate_session=cs,
            trial=sim,
            invite_url=invite_url,
            email_service=email_service,
            now=now,
        )
    except Exception:
        await _rollback_if_supported(db)
        if fresh_candidate_session:
            repo_name = build_candidate_repo_name(
                settings.github.GITHUB_REPO_PREFIX, cs
            )
            await _cleanup_candidate_repo(
                github_client, f"{settings.github.GITHUB_ORG}/{repo_name}"
            )
        raise
    return cs, sim, outcome, invite_url
