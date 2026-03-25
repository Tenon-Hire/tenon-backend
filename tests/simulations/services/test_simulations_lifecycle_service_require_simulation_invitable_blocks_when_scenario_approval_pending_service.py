from __future__ import annotations

import pytest

from tests.simulations.services.simulations_lifecycle_service_utils import *


def test_require_simulation_invitable_blocks_when_scenario_approval_pending():
    sim = _simulation(sim_service.SIMULATION_STATUS_ACTIVE_INVITING)
    sim.pending_scenario_version_id = 22
    with pytest.raises(ApiError) as excinfo:
        sim_service.require_simulation_invitable(sim)
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SCENARIO_APPROVAL_PENDING"
