from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_repository_owned_for_update_and_include_terminated_filter(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="owned-filter@test.com"
    )
    trial, _ = await create_trial(async_session, created_by=talent_partner)

    owned = await repository_owned.get_owned(
        async_session,
        trial.id,
        talent_partner.id,
        for_update=True,
    )
    assert owned is not None

    trial.status = TRIAL_STATUS_TERMINATED
    await async_session.commit()

    filtered_sim, filtered_tasks = await repository_owned.get_owned_with_tasks(
        async_session,
        trial.id,
        talent_partner.id,
        include_terminated=False,
    )
    assert filtered_sim is None
    assert filtered_tasks == []
