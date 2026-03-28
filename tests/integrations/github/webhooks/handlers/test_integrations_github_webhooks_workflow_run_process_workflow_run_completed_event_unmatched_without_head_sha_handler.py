from __future__ import annotations

import pytest

from tests.integrations.github.webhooks.handlers.integrations_github_webhooks_workflow_run_handler_utils import *


@pytest.mark.asyncio
async def test_process_workflow_run_completed_event_unmatched_without_head_sha(
    async_session,
):
    result = await workflow_run.process_workflow_run_completed_event(
        async_session,
        payload=_workflow_payload(
            run_id=9910,
            repo_full_name="acme/no-head-sha",
            head_sha=None,
        ),
        delivery_id="delivery-no-head-sha",
    )

    assert result.outcome == "unmatched"
    assert result.reason_code == "mapping_unmatched"
    assert result.workflow_run_id == 9910
