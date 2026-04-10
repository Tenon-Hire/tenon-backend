from __future__ import annotations

import pytest

from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import *


@pytest.mark.asyncio
async def test_process_evaluation_run_job_invalid_payload():
    response = await winoe_report_pipeline.process_evaluation_run_job(
        {"candidateSessionId": True, "companyId": 2}
    )
    assert response == {
        "status": "skipped_invalid_payload",
        "candidateSessionId": None,
        "companyId": 2,
    }
