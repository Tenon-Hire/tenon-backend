from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_resolve_company_id_raises_when_simulation_missing(async_session):
    task, _, candidate_session = await _setup_handoff_context(
        async_session,
        "service-company-missing@test.com",
    )
    candidate_session.__dict__.pop("simulation", None)

    with pytest.raises(HTTPException) as exc_info:
        await _resolve_company_id(
            async_session,
            candidate_session=candidate_session,
            simulation_id=task.simulation_id + 999_999,
        )
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Simulation metadata unavailable"
