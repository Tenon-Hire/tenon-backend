from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.evaluations.repositories import EVALUATION_RUN_STATUS_RUNNING
from app.evaluations.services import (
    evaluations_services_evaluations_runs_start_service as start_service,
)
from tests.evaluations.services.evaluations_runs_utils import _seed_candidate_session


@pytest.mark.asyncio
async def test_start_run_allows_logger_none(async_session):
    candidate_session = await _seed_candidate_session(async_session)

    started = await start_service.start_run(
        async_session,
        candidate_session_id=candidate_session.id,
        scenario_version_id=candidate_session.scenario_version_id,
        model_name="gpt-5-evaluator",
        model_version="2026-03-11",
        prompt_version="prompt.v4",
        rubric_version="rubric.v2",
        day2_checkpoint_sha="day2-sha",
        day3_final_sha="day3-sha",
        cutoff_commit_sha="cutoff-sha",
        transcript_reference="transcript:hash:no-logger",
        started_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
        logger=None,
        commit=False,
    )

    assert started.id is not None
    assert started.status == EVALUATION_RUN_STATUS_RUNNING
