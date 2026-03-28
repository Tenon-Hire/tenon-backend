from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_github_workflow_artifact_parse_utils import *


@pytest.mark.asyncio
async def test_handle_github_workflow_artifact_parse_skips_invalid_payload():
    result = await parse_handler.handle_github_workflow_artifact_parse(
        {"submissionId": None}
    )

    assert result["status"] == "skipped_invalid_payload"
