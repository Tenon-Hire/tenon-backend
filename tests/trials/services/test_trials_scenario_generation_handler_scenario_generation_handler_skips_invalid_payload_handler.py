from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_skips_invalid_payload() -> None:
    result = await scenario_handler.handle_scenario_generation({"trialId": False})
    assert result == {"status": "skipped_invalid_payload", "trialId": None}
