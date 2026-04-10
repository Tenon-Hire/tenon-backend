from __future__ import annotations

import pytest

from tests.trials.services.trials_lifecycle_service_utils import *


def test_require_trial_invitable_terminated_raises_specific_error():
    sim = _trial(sim_service.TRIAL_STATUS_TERMINATED)
    with pytest.raises(ApiError) as excinfo:
        sim_service.require_trial_invitable(sim)
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "TRIAL_TERMINATED"
