from __future__ import annotations

from tests.integrations.github.webhooks.handlers.integrations_github_webhooks_workflow_run_handler_utils import *


def test_parse_workflow_run_completed_event_rejects_invalid_payload_shapes():
    assert workflow_run.parse_workflow_run_completed_event({}) is None
    assert (
        workflow_run.parse_workflow_run_completed_event(
            {
                "repository": {"full_name": "acme/repo"},
                "workflow_run": {"id": "not-an-int"},
            }
        )
        is None
    )
    assert (
        workflow_run.parse_workflow_run_completed_event(
            {
                "repository": {"full_name": "   "},
                "workflow_run": {"id": 1},
            }
        )
        is None
    )
