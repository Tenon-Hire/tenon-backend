from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


def test_raise_patch_validation_error_allows_missing_field():
    with pytest.raises(ApiError) as excinfo:
        scenario_service._raise_patch_validation_error("invalid payload")
    assert excinfo.value.error_code == "SCENARIO_PATCH_INVALID"
    assert excinfo.value.details == {}
