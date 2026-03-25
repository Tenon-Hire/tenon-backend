from __future__ import annotations

from tests.simulations.services.simulations_lifecycle_service_utils import *


def test_normalize_simulation_status_or_raise_valid_value():
    assert (
        sim_service.normalize_simulation_status_or_raise("active")
        == sim_service.SIMULATION_STATUS_ACTIVE_INVITING
    )
