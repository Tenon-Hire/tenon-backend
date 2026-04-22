from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_github_workflow_artifact_parse_utils import *


@pytest.mark.asyncio
async def test_build_actions_runner_returns_configured_runner_and_client():
    runner, github_client = parse_handler._build_actions_runner()
    try:
        assert (
            runner.workflow_file
            == parse_handler.settings.github.GITHUB_ACTIONS_WORKFLOW_FILE
        )
        assert runner.workflow_file == "evidence-capture.yml"
        assert runner.poll_interval_seconds == 2.0
        assert runner.max_poll_seconds == 90.0
    finally:
        await github_client.aclose()
