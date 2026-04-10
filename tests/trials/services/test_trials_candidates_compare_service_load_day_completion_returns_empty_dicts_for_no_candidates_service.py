from __future__ import annotations

import pytest

from tests.trials.services.trials_candidates_compare_service_utils import *


@pytest.mark.asyncio
async def test_load_day_completion_returns_empty_dicts_for_no_candidates():
    completion, latest = await compare_service._load_day_completion(
        _FakeDB([]),
        trial_id=77,
        candidate_session_ids=[],
    )

    assert completion == {}
    assert latest == {}
