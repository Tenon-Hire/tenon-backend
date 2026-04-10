from __future__ import annotations

import pytest

from tests.trials.services.trials_candidates_compare_service_utils import *


@pytest.mark.asyncio
async def test_require_trial_compare_access_raises_404_when_not_found():
    db = _FakeDB([_ScalarResult(None)])
    user = SimpleNamespace(id=100, company_id=5)

    with pytest.raises(HTTPException) as exc:
        await require_trial_compare_access(db, trial_id=77, user=user)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Trial not found"
