from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_runs_utils import *


@pytest.mark.asyncio
async def test_complete_and_fail_run_not_found(async_session):
    with pytest.raises(eval_service.EvaluationRunStateError, match="not found"):
        await eval_service.complete_run(
            async_session,
            run_id=999999,
            day_scores=_day_scores_payload(),
        )
    with pytest.raises(eval_service.EvaluationRunStateError, match="not found"):
        await eval_service.fail_run(async_session, run_id=999999)
