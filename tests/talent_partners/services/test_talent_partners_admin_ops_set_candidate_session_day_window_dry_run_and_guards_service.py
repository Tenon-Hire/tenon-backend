from __future__ import annotations

import pytest
from sqlalchemy import select

from app.shared.database.shared_database_models_model import AdminActionAudit
from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_set_candidate_session_day_window_dry_run_is_non_mutating(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="day-window-dry@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="claimed",
        invite_email="candidate-day-window-dry@test.com",
        candidate_auth0_sub="candidate:candidate-day-window-dry@test.com",
        claimed_at=datetime(2026, 4, 3, 15, 0, tzinfo=UTC),
    )
    await async_session.commit()
    candidate_session_id = candidate_session.id

    result = await admin_ops_service.set_candidate_session_day_window(
        async_session,
        candidate_session_id=candidate_session_id,
        target_day_index=2,
        reason="preview day two",
        candidate_timezone="America/New_York",
        minutes_already_open=5,
        minutes_until_cutoff=15,
        window_start_local=None,
        window_end_local=None,
        dry_run=True,
        now=datetime(2026, 4, 3, 16, 30, tzinfo=UTC),
    )

    assert result.status == "dry_run"
    assert result.audit_id is None
    refreshed = await async_session.get(type(candidate_session), candidate_session_id)
    assert refreshed is not None
    assert refreshed.status == "claimed"
    assert refreshed.scheduled_start_at is None
    assert refreshed.day_windows_json is None

    audit_ids = (
        (await async_session.execute(select(AdminActionAudit.id))).scalars().all()
    )
    assert audit_ids == []


@pytest.mark.asyncio
async def test_set_candidate_session_day_window_requires_claimed_session(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="day-window-guard@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="not_started",
        invite_email="candidate-day-window-guard@test.com",
    )
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await admin_ops_service.set_candidate_session_day_window(
            async_session,
            candidate_session_id=candidate_session.id,
            target_day_index=2,
            reason="force day two",
            candidate_timezone="America/New_York",
            minutes_already_open=5,
            minutes_until_cutoff=15,
            window_start_local=None,
            window_end_local=None,
            dry_run=False,
            now=datetime(2026, 4, 3, 16, 30, tzinfo=UTC),
        )

    assert excinfo.value.error_code == admin_ops_service.UNSAFE_OPERATION_ERROR_CODE
