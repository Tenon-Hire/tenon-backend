"""Application module for submissions routes submissions github webhooks utils routes workflows."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException, Request


def log_delivery(
    logger: logging.Logger,
    *,
    delivery_id: str | None,
    event_type: str,
    action: str | None = None,
    run_id: int | None = None,
    submission_id: int | None = None,
    outcome: str,
    reason_code: str,
    enqueued_artifact_parse: bool = False,
    level: int = logging.INFO,
) -> None:
    """Execute log delivery."""
    logger.log(
        level,
        "github_webhook_delivery",
        extra={
            "github_delivery_id": delivery_id,
            "event_type": event_type,
            "action": action,
            "run_id": run_id,
            "submission_id": submission_id,
            "outcome": outcome,
            "reason_code": reason_code,
            "enqueued_artifact_parse": enqueued_artifact_parse,
        },
    )


def apply_rate_limit(rate_limit_module: Any, request: Request, rule: Any) -> None:
    """Apply rate limit."""
    if rate_limit_module.rate_limit_enabled():
        client_fingerprint = rate_limit_module.hash_value(
            rate_limit_module.client_id(request)
        )
        key = rate_limit_module.rate_limit_key("github_webhooks", client_fingerprint)
        rate_limit_module.limiter.allow(key, rule)


def parse_payload(
    raw_body: bytes,
    delivery_id: str | None,
    event_type: str,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Parse payload."""
    try:
        payload: Any = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        log_delivery(
            logger,
            delivery_id=delivery_id,
            event_type=event_type,
            outcome="ignored",
            reason_code="payload_json_invalid",
        )
        raise HTTPException(status_code=400, detail="Malformed JSON payload.") from exc
    if not isinstance(payload, dict):
        log_delivery(
            logger,
            delivery_id=delivery_id,
            event_type=event_type,
            outcome="ignored",
            reason_code="payload_not_object",
        )
        raise HTTPException(status_code=400, detail="Malformed JSON payload.")
    return payload
