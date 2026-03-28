"""Application module for submissions routes submissions github webhooks routes workflows."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_handler import (
    process_workflow_run_completed_event,
)
from app.integrations.github.webhooks.integrations_github_webhooks_signature_utils import (
    verify_github_signature,
)
from app.shared.auth import rate_limit
from app.shared.database import get_session
from app.submissions.routes.submissions_routes_submissions_github_webhooks_utils_routes import (
    apply_rate_limit,
    log_delivery,
    parse_payload,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/github/webhooks")
GITHUB_WEBHOOK_RATE_LIMIT = rate_limit.RateLimitRule(limit=240, window_seconds=60.0)


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive Github Webhook",
    description=(
        "Validate GitHub webhook deliveries, process completed workflow_run"
        " events, and enqueue artifact parse jobs."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Webhook signature is invalid."},
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
            "description": "Webhook payload exceeded configured max size."
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Webhook secret not configured."
        },
    },
)
async def receive_github_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """Ingest GitHub workflow webhook deliveries and enqueue artifact parsing."""
    delivery_id = (request.headers.get("X-GitHub-Delivery") or "").strip() or None
    event_type = (request.headers.get("X-GitHub-Event") or "").strip().lower()
    apply_rate_limit(rate_limit, request, GITHUB_WEBHOOK_RATE_LIMIT)

    webhook_secret = (settings.github.GITHUB_WEBHOOK_SECRET or "").strip()
    if not webhook_secret:
        log_delivery(
            logger,
            delivery_id=delivery_id,
            event_type=event_type,
            outcome="webhook_unavailable",
            reason_code="webhook_secret_not_configured",
            level=logging.WARNING,
        )
        raise HTTPException(
            status_code=503, detail="GitHub webhook secret is not configured."
        )

    raw_body = await request.body()
    if len(raw_body) > int(settings.github.GITHUB_WEBHOOK_MAX_BODY_BYTES):
        log_delivery(
            logger,
            delivery_id=delivery_id,
            event_type=event_type,
            outcome="ignored",
            reason_code="payload_too_large",
        )
        raise HTTPException(status_code=413, detail="Webhook payload too large.")

    signature_header = request.headers.get("X-Hub-Signature-256")
    if not verify_github_signature(webhook_secret, raw_body, signature_header):
        log_delivery(
            logger,
            delivery_id=delivery_id,
            event_type=event_type,
            outcome="signature_invalid",
            reason_code="signature_invalid",
            level=logging.WARNING,
        )
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    payload = parse_payload(raw_body, delivery_id, event_type, logger)
    action = (payload.get("action") or "").strip().lower()
    if event_type != "workflow_run" or action != "completed":
        log_delivery(
            logger,
            delivery_id=delivery_id,
            event_type=event_type,
            action=action or None,
            outcome="ignored",
            reason_code="unsupported_event_or_action",
        )
        return {"status": "accepted"}

    result = await process_workflow_run_completed_event(
        db,
        payload=payload,
        delivery_id=delivery_id,
    )
    log_delivery(
        logger,
        delivery_id=delivery_id,
        event_type=event_type,
        action=action,
        run_id=result.workflow_run_id,
        submission_id=result.submission_id,
        outcome=result.outcome,
        reason_code=result.reason_code,
        enqueued_artifact_parse=result.enqueued_artifact_parse,
    )
    return {"status": "accepted"}


__all__ = ["router"]
