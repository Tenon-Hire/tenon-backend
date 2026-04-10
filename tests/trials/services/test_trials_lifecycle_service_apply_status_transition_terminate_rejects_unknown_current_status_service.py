from __future__ import annotations

import pytest

from tests.trials.services.trials_lifecycle_service_utils import *


def test_apply_status_transition_terminate_rejects_unknown_current_status():
    sim = _trial("legacy_unknown")
    with pytest.raises(ApiError) as excinfo:
        sim_service.apply_status_transition(
            sim,
            target_status=sim_service.TRIAL_STATUS_TERMINATED,
            changed_at=datetime.now(UTC),
        )
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "TRIAL_INVALID_STATUS_TRANSITION"
