from __future__ import annotations

import pytest

from tests.simulations.services.simulations_candidates_compare_service_utils import *


@pytest.mark.asyncio
async def test_require_simulation_compare_access_raises_403_for_non_owner():
    simulation = SimpleNamespace(id=77, company_id=5, created_by=101)
    db = _FakeDB([_ScalarResult(simulation)])
    user = SimpleNamespace(id=100, company_id=5)

    with pytest.raises(HTTPException) as exc:
        await require_simulation_compare_access(db, simulation_id=77, user=user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Simulation access forbidden"
