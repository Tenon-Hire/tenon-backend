from __future__ import annotations

import pytest

from tests.simulations.services.simulations_lifecycle_service_utils import *


def test_require_simulation_invitable_terminated_raises_specific_error():
    sim = _simulation(sim_service.SIMULATION_STATUS_TERMINATED)
    with pytest.raises(ApiError) as excinfo:
        sim_service.require_simulation_invitable(sim)
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SIMULATION_TERMINATED"
