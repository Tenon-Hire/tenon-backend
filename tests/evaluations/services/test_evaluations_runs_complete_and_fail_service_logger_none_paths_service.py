from __future__ import annotations

import pytest

from app.evaluations.services import (
    evaluations_services_evaluations_runs_complete_service as complete_service,
)
from app.evaluations.services import (
    evaluations_services_evaluations_runs_fail_service as fail_service,
)
from tests.evaluations.services.evaluations_runs_utils import (
    EVALUATION_RUN_STATUS_COMPLETED,
    EVALUATION_RUN_STATUS_FAILED,
    _day_scores_payload,
    _seed_candidate_session,
    eval_service,
)


async def _start_run(async_session, *, transcript_reference: str):
    candidate_session = await _seed_candidate_session(async_session)
    return await eval_service.start_run(
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
        transcript_reference=transcript_reference,
    )


@pytest.mark.asyncio
async def test_complete_run_impl_allows_logger_none(async_session):
    started = await _start_run(
        async_session, transcript_reference="transcript:none:complete"
    )
    completed = await complete_service.complete_run(
        async_session,
        run_id=started.id,
        day_scores=_day_scores_payload(),
        commit=False,
        logger=None,
    )

    assert completed.status == EVALUATION_RUN_STATUS_COMPLETED


@pytest.mark.asyncio
async def test_fail_run_impl_allows_logger_none(async_session):
    started = await _start_run(
        async_session, transcript_reference="transcript:none:fail"
    )
    failed = await fail_service.fail_run(
        async_session,
        run_id=started.id,
        error_code="model_timeout",
        commit=False,
        logger=None,
    )

    assert failed.status == EVALUATION_RUN_STATUS_FAILED
