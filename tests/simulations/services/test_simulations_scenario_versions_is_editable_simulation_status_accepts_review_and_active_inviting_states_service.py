from __future__ import annotations

from tests.simulations.services.simulations_scenario_versions_service_utils import *


def test_is_editable_simulation_status_accepts_review_and_active_inviting_states():
    assert scenario_service._is_editable_simulation_status("ready_for_review") is True
    assert scenario_service._is_editable_simulation_status("active_inviting") is True
    assert scenario_service._is_editable_simulation_status("draft") is False
    assert scenario_service._is_editable_simulation_status("generating") is False
    assert scenario_service._is_editable_simulation_status("terminated") is False
    assert scenario_service._is_editable_simulation_status(None) is False
