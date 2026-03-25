from __future__ import annotations

import json

import pytest

from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_handler import (
    WorkflowRunWebhookOutcome,
)
from app.shared.http.routes import github_webhooks as webhook_routes
from tests.submissions.routes.submissions_github_webhooks_routes_utils import (
    headers_for_payload,
)


@pytest.mark.asyncio
async def test_github_webhook_unknown_event_returns_202(async_client, monkeypatch):
    webhook_routes.rate_limit.limiter.reset()
    secret = "test-webhook-secret"
    monkeypatch.setattr(webhook_routes.settings.github, "GITHUB_WEBHOOK_SECRET", secret)
    raw_body = json.dumps({"action": "created"}).encode("utf-8")
    response = await async_client.post(
        "/api/github/webhooks",
        content=raw_body,
        headers=headers_for_payload(
            secret=secret,
            raw_body=raw_body,
            event_type="ping",
            delivery_id="unknown-event",
        ),
    )
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}


@pytest.mark.asyncio
async def test_github_webhook_unknown_workflow_action_returns_202(
    async_client, monkeypatch
):
    webhook_routes.rate_limit.limiter.reset()
    secret = "test-webhook-secret"
    monkeypatch.setattr(webhook_routes.settings.github, "GITHUB_WEBHOOK_SECRET", secret)
    raw_body = json.dumps({"action": "requested"}).encode("utf-8")
    response = await async_client.post(
        "/api/github/webhooks",
        content=raw_body,
        headers=headers_for_payload(
            secret=secret,
            raw_body=raw_body,
            event_type="workflow_run",
            delivery_id="unknown-action",
        ),
    )
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}


@pytest.mark.asyncio
async def test_github_webhook_completed_event_accepted_and_rate_limited(
    async_client, monkeypatch
):
    webhook_routes.rate_limit.limiter.reset()
    secret = "test-webhook-secret"
    monkeypatch.setattr(webhook_routes.settings.github, "GITHUB_WEBHOOK_SECRET", secret)
    monkeypatch.setattr(webhook_routes.rate_limit, "rate_limit_enabled", lambda: True)
    observed_rate_limit_keys: list[str] = []
    monkeypatch.setattr(
        webhook_routes.rate_limit.limiter,
        "allow",
        lambda key, _rule: observed_rate_limit_keys.append(key) or None,
    )

    async def _stub_process(*_args, **_kwargs):
        return WorkflowRunWebhookOutcome(
            outcome="updated_status",
            reason_code="matched_by_workflow_run_id",
            submission_id=42,
            workflow_run_id=9001,
            enqueued_artifact_parse=True,
        )

    monkeypatch.setattr(
        webhook_routes, "process_workflow_run_completed_event", _stub_process
    )
    payload = {
        "action": "completed",
        "repository": {"full_name": "acme/repo"},
        "workflow_run": {"id": 9001, "head_sha": "abc123"},
    }
    raw_body = json.dumps(payload).encode("utf-8")
    response = await async_client.post(
        "/api/github/webhooks",
        content=raw_body,
        headers=headers_for_payload(
            secret=secret,
            raw_body=raw_body,
            event_type="workflow_run",
            delivery_id="completed-accepted",
        ),
    )
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    assert len(observed_rate_limit_keys) == 1
    assert observed_rate_limit_keys[0].startswith("github_webhooks:")
