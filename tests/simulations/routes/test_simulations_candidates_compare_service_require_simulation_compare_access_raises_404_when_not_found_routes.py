from __future__ import annotations

import pytest

from tests.simulations.services.simulations_candidates_compare_service_utils import *


@pytest.mark.asyncio
async def test_require_simulation_compare_access_raises_404_when_not_found():
    db = _FakeDB([_ScalarResult(None)])
    user = SimpleNamespace(id=100, company_id=5)

    with pytest.raises(HTTPException) as exc:
        await require_simulation_compare_access(db, simulation_id=77, user=user)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Simulation not found"
