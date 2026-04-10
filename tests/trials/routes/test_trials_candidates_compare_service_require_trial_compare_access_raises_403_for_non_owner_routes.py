from __future__ import annotations

import pytest

from tests.trials.services.trials_candidates_compare_service_utils import *


@pytest.mark.asyncio
async def test_require_trial_compare_access_raises_403_for_non_owner():
    trial = SimpleNamespace(id=77, company_id=5, created_by=101)
    db = _FakeDB([_ScalarResult(trial)])
    user = SimpleNamespace(id=100, company_id=5)

    with pytest.raises(HTTPException) as exc:
        await require_trial_compare_access(db, trial_id=77, user=user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Trial access forbidden"
