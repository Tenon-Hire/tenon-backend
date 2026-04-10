from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Trial,
)

from .shared_factories_candidate_session_helpers_utils import (
    _resolve_candidate_session_scenario_version_id,
    _resolve_schedule_defaults,
)


async def create_candidate_session(
    session: AsyncSession,
    *,
    trial: Trial,
    candidate_name: str = "Jane Candidate",
    invite_email: str = "jane@example.com",
    status: str = "not_started",
    token: str | None = None,
    expires_in_days: int = 14,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    candidate_email: str | None = None,
    candidate_auth0_sub: str | None = None,
    claimed_at: datetime | None = None,
    scheduled_start_at: datetime | None = None,
    candidate_timezone: str | None = None,
    day_windows_json: list[dict] | None = None,
    schedule_locked_at: datetime | None = None,
    with_default_schedule: bool = False,
    scenario_version_id: int | None = None,
    consent_version: str | None = None,
    consent_timestamp: datetime | None = None,
    ai_notice_version: str | None = None,
) -> CandidateSession:
    (
        resolved_scheduled_start,
        resolved_timezone,
        resolved_day_windows,
    ) = _resolve_schedule_defaults(
        with_default_schedule=with_default_schedule,
        scheduled_start_at=scheduled_start_at,
        candidate_timezone=candidate_timezone,
        day_windows_json=day_windows_json,
    )
    resolved_scenario_version_id = await _resolve_candidate_session_scenario_version_id(
        session,
        trial=trial,
        scenario_version_id=scenario_version_id,
    )
    consent_time = (
        (consent_timestamp or datetime.now(UTC))
        if consent_version is not None
        else None
    )
    cs = CandidateSession(
        trial_id=trial.id,
        scenario_version_id=resolved_scenario_version_id,
        candidate_user_id=None,
        candidate_name=candidate_name,
        invite_email=invite_email,
        token=token or secrets.token_urlsafe(16),
        candidate_email=candidate_email,
        candidate_auth0_sub=candidate_auth0_sub,
        claimed_at=claimed_at,
        status=status,
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
        started_at=started_at,
        completed_at=completed_at,
        scheduled_start_at=resolved_scheduled_start,
        candidate_timezone=resolved_timezone,
        day_windows_json=resolved_day_windows,
        schedule_locked_at=schedule_locked_at,
        consent_version=consent_version,
        consent_timestamp=consent_time,
        ai_notice_version=(
            (ai_notice_version if ai_notice_version is not None else consent_version)
            if consent_version is not None
            else ai_notice_version
        ),
    )
    session.add(cs)
    await session.flush()
    return cs
