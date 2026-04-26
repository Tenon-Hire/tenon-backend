"""Application module for trials services trials invite workflow service workflows."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github import GithubClient
from app.notifications.services import service as notification_service
from app.shared.time.shared_time_now_service import utcnow as shared_utcnow
from app.trials import services as sim_service
from app.trials.services import (
    trials_services_trials_invite_preprovision_service as invite_preprovision,
)

logger = logging.getLogger(__name__)


async def _rollback_if_supported(db: AsyncSession) -> None:
    rollback = getattr(db, "rollback", None)
    if callable(rollback):
        await rollback()


async def _cleanup_provisioned_repos(
    github_client: GithubClient, repo_full_names: tuple[str, ...] | list[str]
) -> None:
    delete_repo = getattr(github_client, "delete_repo", None)
    if not callable(delete_repo):
        return
    for repo_full_name in dict.fromkeys(repo_full_names):
        try:
            await delete_repo(repo_full_name)
        except Exception:
            logger.warning(
                "github_workspace_preprovision_cleanup_failed",
                extra={"repo_full_name": repo_full_name},
            )


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
    provisioned_repo_full_names: tuple[str, ...] = ()
    try:
        provisioned_repo_full_names = await invite_preprovision.preprovision_workspaces(
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
    except Exception as exc:
        if fresh_candidate_session:
            cleanup_targets = getattr(exc, "provisioned_repo_full_names", ())
            if not cleanup_targets:
                cleanup_targets = provisioned_repo_full_names
            if cleanup_targets is None:
                cleanup_targets = ()
            await _cleanup_provisioned_repos(
                github_client,
                tuple(cleanup_targets),
            )
        await _rollback_if_supported(db)
        raise
    return cs, sim, outcome, invite_url
