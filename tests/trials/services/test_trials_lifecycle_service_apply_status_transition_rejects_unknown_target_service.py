from __future__ import annotations

import pytest

from tests.trials.services.trials_lifecycle_service_utils import *


def test_apply_status_transition_rejects_unknown_target():
    sim = _trial(trial_service.TRIAL_STATUS_READY_FOR_REVIEW)
    with pytest.raises(ValueError):
        trial_service.apply_status_transition(sim, target_status="unsupported_status")
