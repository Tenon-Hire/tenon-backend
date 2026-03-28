from __future__ import annotations

import pytest

from tests.simulations.services.simulations_lifecycle_service_utils import *


def test_apply_status_transition_rejects_unknown_target():
    sim = _simulation(sim_service.SIMULATION_STATUS_READY_FOR_REVIEW)
    with pytest.raises(ValueError):
        sim_service.apply_status_transition(sim, target_status="unsupported_status")
