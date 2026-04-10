from __future__ import annotations

from tests.trials.services.trials_lifecycle_service_utils import *


def test_normalize_trial_status_strictness():
    assert (
        sim_service.normalize_trial_status("active")
        == sim_service.TRIAL_STATUS_ACTIVE_INVITING
    )
    assert (
        sim_service.normalize_trial_status(sim_service.TRIAL_STATUS_DRAFT)
        == sim_service.TRIAL_STATUS_DRAFT
    )
    assert sim_service.normalize_trial_status("unknown_status") is None
    assert sim_service.normalize_trial_status(None) is None
