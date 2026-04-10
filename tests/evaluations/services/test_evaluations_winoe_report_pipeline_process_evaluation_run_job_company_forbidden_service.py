from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import *


@pytest.mark.asyncio
async def test_process_evaluation_run_job_company_forbidden(monkeypatch):
    db = SimpleNamespace()
    context = SimpleNamespace(
        candidate_session=SimpleNamespace(id=10, scenario_version_id=12),
        trial=SimpleNamespace(id=14, company_id=200, ai_eval_enabled_by_day={}),
        scenario_version=None,
    )
    monkeypatch.setattr(
        winoe_report_pipeline,
        "async_session_maker",
        _session_maker_for(db),
    )
    monkeypatch.setattr(
        winoe_report_pipeline,
        "get_candidate_session_evaluation_context",
        AsyncMock(return_value=context),
    )
    monkeypatch.setattr(
        winoe_report_pipeline, "has_company_access", lambda **_kwargs: False
    )

    response = await winoe_report_pipeline.process_evaluation_run_job(
        {"candidateSessionId": 10, "companyId": 201}
    )
    assert response == {"status": "company_access_forbidden", "candidateSessionId": 10}
