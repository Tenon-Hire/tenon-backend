"""Application module for trials services trials invite workflow service workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github import GithubClient
from app.notifications.services import service as notification_service
from app.shared.time.shared_time_now_service import utcnow as shared_utcnow
from app.trials import services as sim_service
from app.trials.services import (
    trials_services_trials_codespace_specializer_service as codespace_specializer,
)
from app.trials.services import (
    trials_services_trials_invite_preprovision_service as invite_preprovision,
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
    await codespace_specializer.ensure_precommit_bundle_ready_for_invites(
        db,
        trial=sim,
        scenario_version=scenario_version,
        tasks=tasks,
    )
    cs, outcome = await sim_service.create_or_resend_invite(
        db,
        trial_id,
        payload,
        scenario_version_id=scenario_version.id,
        now=now,
    )
    await invite_preprovision.preprovision_workspaces(
        db,
        cs,
        tasks,
        github_client,
        now=now,
        fresh_candidate_session=bool(getattr(cs, "_invite_newly_created", False)),
    )
    invite_url = sim_service.invite_url(cs.token)
    await notification_service.send_invite_email(
        db,
        candidate_session=cs,
        trial=sim,
        invite_url=invite_url,
        email_service=email_service,
        now=now,
    )
    return cs, sim, outcome, invite_url
