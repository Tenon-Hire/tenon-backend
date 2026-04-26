from __future__ import annotations

from tests.trials.services.trials_lifecycle_service_utils import *


def test_normalize_trial_status_or_raise_valid_value():
    assert (
        trial_service.normalize_trial_status_or_raise("active")
        == trial_service.TRIAL_STATUS_ACTIVE_INVITING
    )
