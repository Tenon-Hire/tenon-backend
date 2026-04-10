from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.asyncio
async def test_request_scenario_regeneration_missing_trial_returns_404(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="scenario-regen-missing@test.com"
    )
    with pytest.raises(HTTPException) as excinfo:
        await scenario_service.request_scenario_regeneration(
            async_session,
            trial_id=999999,
            actor_user_id=talent_partner.id,
        )
    assert excinfo.value.status_code == 404
