from __future__ import annotations

import pytest

from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_reset_candidate_session_dry_run_is_non_mutating(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="reset-dry-owner@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="in_progress",
        candidate_auth0_sub="auth0|candidate-reset-dry",
        candidate_email="candidate-reset-dry@test.com",
        started_at=datetime.now(UTC) - timedelta(hours=1),
        with_default_schedule=True,
    )
    candidate_session_id = candidate_session.id
    await async_session.commit()

    result = await admin_ops_service.reset_candidate_session(
        async_session,
        actor=_actor(),
        candidate_session_id=candidate_session_id,
        target_state="not_started",
        reason="  Demo   dry\nrun reset  ",
        override_if_evaluated=False,
        dry_run=True,
        now=datetime(2026, 1, 2, 10, 30, 0),
    )
    assert result.status == "dry_run"
    assert result.audit_id is None

    refreshed = await async_session.get(type(candidate_session), candidate_session_id)
    assert refreshed is not None
    assert refreshed.status == "in_progress"
    assert refreshed.candidate_auth0_sub == "auth0|candidate-reset-dry"
    assert refreshed.started_at is not None

    audits = (
        (
            await async_session.execute(
                select(AdminActionAudit).where(
                    AdminActionAudit.action
                    == admin_ops_service.CANDIDATE_SESSION_RESET_ACTION
                )
            )
        )
        .scalars()
        .all()
    )
    assert audits == []
