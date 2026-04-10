from __future__ import annotations

import pytest

from tests.candidates.services.candidates_session_service_utils import *


@pytest.mark.asyncio
async def test_load_tasks_empty(async_session):
    talent_partner = await create_talent_partner(async_session, email="empty@sim.com")
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    for t in tasks:
        await async_session.delete(t)
    await async_session.commit()
    with pytest.raises(HTTPException) as excinfo:
        await cs_service.load_tasks(async_session, sim.id)
    assert excinfo.value.status_code == 500
