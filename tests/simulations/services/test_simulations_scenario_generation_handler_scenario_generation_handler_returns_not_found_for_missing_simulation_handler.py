from __future__ import annotations

import pytest

from tests.simulations.services.simulations_scenario_generation_handler_utils import *


@pytest.mark.asyncio
async def test_scenario_generation_handler_returns_not_found_for_missing_simulation() -> (
    None
):
    result = await scenario_handler.handle_scenario_generation({"simulationId": 999999})
    assert result == {"status": "simulation_not_found", "simulationId": 999999}
