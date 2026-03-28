from __future__ import annotations

import pytest

from tests.simulations.services.simulations_lifecycle_service_utils import *


def test_apply_status_transition_rejects_invalid_edges():
    sim = _simulation(sim_service.SIMULATION_STATUS_DRAFT)
    with pytest.raises(ApiError) as excinfo:
        sim_service.apply_status_transition(
            sim,
            target_status=sim_service.SIMULATION_STATUS_ACTIVE_INVITING,
            changed_at=datetime.now(UTC),
        )

    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SIMULATION_INVALID_STATUS_TRANSITION"
    assert excinfo.value.details["allowedTransitions"] == [
        sim_service.SIMULATION_STATUS_GENERATING
    ]
