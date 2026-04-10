from __future__ import annotations

from tests.trials.services.trials_scenario_versions_service_utils import *


def test_is_editable_trial_status_accepts_review_and_active_inviting_states():
    assert scenario_service._is_editable_trial_status("ready_for_review") is True
    assert scenario_service._is_editable_trial_status("active_inviting") is True
    assert scenario_service._is_editable_trial_status("draft") is False
    assert scenario_service._is_editable_trial_status("generating") is False
    assert scenario_service._is_editable_trial_status("terminated") is False
    assert scenario_service._is_editable_trial_status(None) is False
