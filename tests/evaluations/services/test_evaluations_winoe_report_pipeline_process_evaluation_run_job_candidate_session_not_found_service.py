from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import *


@pytest.mark.asyncio
async def test_process_evaluation_run_job_candidate_session_not_found(monkeypatch):
    db = SimpleNamespace()
    monkeypatch.setattr(
        winoe_report_pipeline,
        "async_session_maker",
        _session_maker_for(db),
    )
    monkeypatch.setattr(
        winoe_report_pipeline,
        "get_candidate_session_evaluation_context",
        AsyncMock(return_value=None),
    )

    response = await winoe_report_pipeline.process_evaluation_run_job(
        {"candidateSessionId": 10, "companyId": 20}
    )
    assert response == {
        "status": "candidate_session_not_found",
        "candidateSessionId": 10,
    }
