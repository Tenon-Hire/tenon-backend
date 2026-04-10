from __future__ import annotations

import pytest

from tests.trials.services.trials_core_service_utils import *


@pytest.mark.asyncio
async def test_require_owned_trial_with_tasks_raises(monkeypatch):
    async def _return_none(*_a, **_k):
        return None, []

    monkeypatch.setattr(sim_service.sim_repo, "get_owned_with_tasks", _return_none)
    with pytest.raises(Exception) as excinfo:
        await sim_service.require_owned_trial_with_tasks(None, 1, 2)
    assert excinfo.value.status_code == 404
