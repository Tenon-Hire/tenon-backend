from __future__ import annotations

import pytest

from tests.integrations.github.webhooks.handlers.integrations_github_webhooks_workflow_run_handler_utils import *


@pytest.mark.asyncio
async def test_process_workflow_run_completed_event_invalid_payload_is_ignored(
    async_session,
):
    result = await workflow_run.process_workflow_run_completed_event(
        async_session,
        payload={"action": "completed"},
        delivery_id="delivery-invalid",
    )

    assert result.outcome == "ignored"
    assert result.reason_code == "workflow_run_payload_invalid"
