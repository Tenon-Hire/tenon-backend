from __future__ import annotations

import pytest

from tests.trials.services.trials_lifecycle_service_utils import *


def test_require_trial_invitable_blocks_when_scenario_approval_pending():
    sim = _trial(sim_service.TRIAL_STATUS_ACTIVE_INVITING)
    sim.pending_scenario_version_id = 22
    with pytest.raises(ApiError) as excinfo:
        sim_service.require_trial_invitable(sim)
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "SCENARIO_APPROVAL_PENDING"
