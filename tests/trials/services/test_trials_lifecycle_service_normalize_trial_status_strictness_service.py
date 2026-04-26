from __future__ import annotations

from tests.trials.services.trials_lifecycle_service_utils import *


def test_normalize_trial_status_strictness():
    assert (
        trial_service.normalize_trial_status("active")
        == trial_service.TRIAL_STATUS_ACTIVE_INVITING
    )
    assert (
        trial_service.normalize_trial_status(trial_service.TRIAL_STATUS_DRAFT)
        == trial_service.TRIAL_STATUS_DRAFT
    )
    assert trial_service.normalize_trial_status("unknown_status") is None
    assert trial_service.normalize_trial_status(None) is None
