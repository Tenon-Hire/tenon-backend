from __future__ import annotations

from tests.integrations.github.webhooks.handlers.integrations_github_webhooks_workflow_run_handler_utils import *


def test_parse_workflow_run_completed_event_normalizes_fields():
    event = workflow_run.parse_workflow_run_completed_event(
        _workflow_payload(
            run_id=123,
            repo_full_name="acme/repo",
            head_sha="abc123",
            run_attempt=None,
            conclusion=777,
            completed_at="2026-03-13T14:30:00",
        )
    )

    assert event is not None
    assert event.workflow_run_id == 123
    assert event.run_attempt is None
    assert event.repo_full_name == "acme/repo"
    assert event.head_sha == "abc123"
    assert event.conclusion is None
    assert event.completed_at == datetime(2026, 3, 13, 14, 30, tzinfo=UTC)
