from __future__ import annotations

from tests.simulations.services.simulations_lifecycle_service_utils import *


def test_normalize_simulation_status_strictness():
    assert (
        sim_service.normalize_simulation_status("active")
        == sim_service.SIMULATION_STATUS_ACTIVE_INVITING
    )
    assert (
        sim_service.normalize_simulation_status(sim_service.SIMULATION_STATUS_DRAFT)
        == sim_service.SIMULATION_STATUS_DRAFT
    )
    assert sim_service.normalize_simulation_status("unknown_status") is None
    assert sim_service.normalize_simulation_status(None) is None
