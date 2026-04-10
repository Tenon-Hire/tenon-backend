from __future__ import annotations

from tests.trials.services.trials_scenario_versions_service_utils import *


def test_is_editable_scenario_status_accepts_only_persisted_ready_state():
    assert scenario_service._is_editable_scenario_status("ready") is True
    assert scenario_service._is_editable_scenario_status("ready_for_review") is False
    assert scenario_service._is_editable_scenario_status("draft") is False
    assert scenario_service._is_editable_scenario_status("generating") is False
    assert scenario_service._is_editable_scenario_status("locked") is False
    assert scenario_service._is_editable_scenario_status(None) is False
