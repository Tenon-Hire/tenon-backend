from __future__ import annotations

import pytest

from tests.recruiters.services.recruiters_admin_ops_utils import *


@pytest.mark.asyncio
async def test_reset_candidate_session_requires_claimant_identity(async_session):
    recruiter = await create_recruiter(
        async_session, email="reset-claimant-owner@test.com"
    )
    simulation, _ = await create_simulation(async_session, created_by=recruiter)
    candidate_session = await create_candidate_session(
        async_session,
        simulation=simulation,
        status="not_started",
        candidate_auth0_sub=None,
    )
    await async_session.commit()

    with pytest.raises(ApiError) as excinfo:
        await admin_ops_service.reset_candidate_session(
            async_session,
            actor=_actor(),
            candidate_session_id=candidate_session.id,
            target_state="claimed",
            reason="no claimant identity",
            override_if_evaluated=False,
            dry_run=False,
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.details["requires"] == "candidate_auth0_sub"
