from __future__ import annotations

import pytest

from tests.trials.services.trials_lifecycle_service_utils import *


def test_normalize_trial_status_or_raise_invalid_value():
    with pytest.raises(ApiError) as excinfo:
        sim_service.normalize_trial_status_or_raise("unknown_status")
    assert excinfo.value.status_code == 500
    assert excinfo.value.error_code == "TRIAL_STATUS_INVALID"
    assert excinfo.value.details == {"status": "unknown_status"}
