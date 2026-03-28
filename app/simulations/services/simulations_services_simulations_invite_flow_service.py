"""Application module for simulations services simulations invite flow service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_core_schema import (
    CandidateInviteRequest,
)
from app.shared.types.shared_types_types_model import CANDIDATE_SESSION_STATUS_COMPLETED

from .simulations_services_simulations_invite_errors_service import InviteRejectedError
from .simulations_services_simulations_invite_factory_service import (
    resolve_create_invite_callable,
)
from .simulations_services_simulations_invite_tokens_service import (
    _invite_is_expired,
    _refresh_invite_token,
)


async def create_or_resend_invite(
    db: AsyncSession,
    simulation_id: int,
    payload: CandidateInviteRequest,
    *,
    scenario_version_id: int | None = None,
    now: datetime | None = None,
) -> tuple:
    """Create or resend invite."""
    now = now or datetime.now(UTC)
    invite_email = str(payload.inviteEmail).strip().lower()

    from app.simulations import services as sim_service

    existing = await sim_service.cs_repo.get_by_simulation_and_email_for_update(
        db, simulation_id=simulation_id, invite_email=invite_email
    )
    if existing:
        existing._invite_newly_created = False
        if existing.status == CANDIDATE_SESSION_STATUS_COMPLETED:
            raise InviteRejectedError()
        if _invite_is_expired(existing, now=now):
            refreshed = await _refresh_invite_token(db, existing, now=now)
            refreshed._invite_newly_created = False
            return refreshed, "created"
        return existing, "resent"

    create_invite_fn = resolve_create_invite_callable()
    kwargs = {
        "db": db,
        "simulation_id": simulation_id,
        "payload": payload,
        "now": now,
    }
    if scenario_version_id is not None:
        kwargs["scenario_version_id"] = scenario_version_id
    try:
        created, was_created = await create_invite_fn(**kwargs)
    except TypeError as exc:
        if scenario_version_id is None or "scenario_version_id" not in str(exc):
            raise
        kwargs.pop("scenario_version_id", None)
        created, was_created = await create_invite_fn(**kwargs)
    created._invite_newly_created = bool(was_created)
    if created.status == CANDIDATE_SESSION_STATUS_COMPLETED:
        raise InviteRejectedError()
    if _invite_is_expired(created, now=now):
        refreshed = await _refresh_invite_token(db, created, now=now)
        refreshed._invite_newly_created = bool(was_created)
        return refreshed, "created"
    return created, "created" if was_created else "resent"
