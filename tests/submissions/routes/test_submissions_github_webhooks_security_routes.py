from __future__ import annotations

import json

import pytest

from app.shared.http.routes import github_webhooks as webhook_routes
from tests.submissions.routes.submissions_github_webhooks_routes_utils import (
    headers_for_payload,
)


@pytest.mark.asyncio
async def test_github_webhook_missing_signature_returns_401(async_client, monkeypatch):
    webhook_routes.rate_limit.limiter.reset()
    secret = "test-webhook-secret"
    monkeypatch.setattr(webhook_routes.settings.github, "GITHUB_WEBHOOK_SECRET", secret)
    raw_body = json.dumps({"action": "completed"}).encode("utf-8")
    response = await async_client.post(
        "/api/github/webhooks",
        content=raw_body,
        headers=headers_for_payload(
            secret=secret,
            raw_body=raw_body,
            event_type="workflow_run",
            delivery_id="missing-signature",
            include_signature=False,
        ),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_github_webhook_invalid_signature_returns_401(async_client, monkeypatch):
    webhook_routes.rate_limit.limiter.reset()
    secret = "test-webhook-secret"
    monkeypatch.setattr(webhook_routes.settings.github, "GITHUB_WEBHOOK_SECRET", secret)
    raw_body = json.dumps({"action": "completed"}).encode("utf-8")
    response = await async_client.post(
        "/api/github/webhooks",
        content=raw_body,
        headers=headers_for_payload(
            secret=secret,
            raw_body=raw_body,
            event_type="workflow_run",
            delivery_id="invalid-signature",
            signature="sha256=0000000000000000000000000000000000000000000000000000000000000000",
        ),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_github_webhook_malformed_json_returns_400(async_client, monkeypatch):
    webhook_routes.rate_limit.limiter.reset()
    secret = "test-webhook-secret"
    monkeypatch.setattr(webhook_routes.settings.github, "GITHUB_WEBHOOK_SECRET", secret)
    raw_body = b"{invalid-json"
    response = await async_client.post(
        "/api/github/webhooks",
        content=raw_body,
        headers=headers_for_payload(
            secret=secret,
            raw_body=raw_body,
            event_type="workflow_run",
            delivery_id="malformed-json",
        ),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_github_webhook_secret_unset_returns_503(async_client, monkeypatch):
    webhook_routes.rate_limit.limiter.reset()
    monkeypatch.setattr(webhook_routes.settings.github, "GITHUB_WEBHOOK_SECRET", "")
    raw_body = json.dumps({"action": "completed"}).encode("utf-8")
    response = await async_client.post(
        "/api/github/webhooks",
        content=raw_body,
        headers=headers_for_payload(
            secret="unused",
            raw_body=raw_body,
            event_type="workflow_run",
            delivery_id="secret-unset",
        ),
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_github_webhook_payload_too_large_returns_413(async_client, monkeypatch):
    webhook_routes.rate_limit.limiter.reset()
    secret = "test-webhook-secret"
    monkeypatch.setattr(webhook_routes.settings.github, "GITHUB_WEBHOOK_SECRET", secret)
    monkeypatch.setattr(
        webhook_routes.settings.github, "GITHUB_WEBHOOK_MAX_BODY_BYTES", 4
    )
    raw_body = b'{"action":"completed"}'
    response = await async_client.post(
        "/api/github/webhooks",
        content=raw_body,
        headers=headers_for_payload(
            secret=secret,
            raw_body=raw_body,
            event_type="workflow_run",
            delivery_id="payload-too-large",
        ),
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_github_webhook_payload_not_object_returns_400(async_client, monkeypatch):
    webhook_routes.rate_limit.limiter.reset()
    secret = "test-webhook-secret"
    monkeypatch.setattr(webhook_routes.settings.github, "GITHUB_WEBHOOK_SECRET", secret)
    raw_body = json.dumps(["not", "an", "object"]).encode("utf-8")
    response = await async_client.post(
        "/api/github/webhooks",
        content=raw_body,
        headers=headers_for_payload(
            secret=secret,
            raw_body=raw_body,
            event_type="workflow_run",
            delivery_id="payload-not-object",
        ),
    )
    assert response.status_code == 400
