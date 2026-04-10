from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_returns_not_found_for_missing_trial() -> (
    None
):
    result = await scenario_handler.handle_scenario_generation({"trialId": 999999})
    assert result == {"status": "trial_not_found", "trialId": 999999}
