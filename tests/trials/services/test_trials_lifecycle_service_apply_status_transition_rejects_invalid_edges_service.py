from __future__ import annotations

import pytest

from tests.trials.services.trials_lifecycle_service_utils import *


def test_apply_status_transition_rejects_invalid_edges():
    sim = _trial(trial_service.TRIAL_STATUS_DRAFT)
    with pytest.raises(ApiError) as excinfo:
        trial_service.apply_status_transition(
            sim,
            target_status=trial_service.TRIAL_STATUS_ACTIVE_INVITING,
            changed_at=datetime.now(UTC),
        )

    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "TRIAL_INVALID_STATUS_TRANSITION"
    assert excinfo.value.details["allowedTransitions"] == [
        trial_service.TRIAL_STATUS_GENERATING
    ]
