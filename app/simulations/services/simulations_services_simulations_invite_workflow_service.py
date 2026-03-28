"""Application module for simulations services simulations invite workflow service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github import GithubClient
from app.notifications.services import service as notification_service
from app.simulations import services as sim_service
from app.simulations.services import (
    simulations_services_simulations_invite_preprovision_service as invite_preprovision,
)


async def create_candidate_invite_workflow(
    db: AsyncSession,
    *,
    simulation_id: int,
    payload,
    user_id: int,
    email_service,
    github_client: GithubClient,
    now: datetime | None = None,
):
    """Create candidate invite workflow."""
    try:
        sim, tasks = await sim_service.require_owned_simulation_with_tasks(
            db,
            simulation_id,
            user_id,
            for_update=True,
        )
    except TypeError as exc:
        if "for_update" not in str(exc):
            raise
        sim, tasks = await sim_service.require_owned_simulation_with_tasks(
            db,
            simulation_id,
            user_id,
        )
    sim_service.require_simulation_invitable(sim)
    now = now or datetime.now(UTC)
    try:
        scenario_version = await sim_service.lock_active_scenario_for_invites(
            db,
            simulation_id=simulation_id,
            now=now,
            simulation=sim,
        )
    except TypeError as exc:
        if "simulation" not in str(exc):
            raise
        scenario_version = await sim_service.lock_active_scenario_for_invites(
            db,
            simulation_id=simulation_id,
            now=now,
        )
    cs, outcome = await sim_service.create_or_resend_invite(
        db,
        simulation_id,
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
        simulation=sim,
        invite_url=invite_url,
        email_service=email_service,
        now=now,
    )
    return cs, sim, outcome, invite_url
