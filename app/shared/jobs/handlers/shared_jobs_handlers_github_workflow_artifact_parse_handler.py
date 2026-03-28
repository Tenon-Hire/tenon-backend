"""Application module for jobs handlers github workflow artifact parse handler workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.config import settings
from app.integrations.github import GithubClient
from app.integrations.github.actions_runner import GithubActionsRunner
from app.integrations.github.webhooks.handlers.integrations_github_webhooks_handlers_workflow_run_handler import (
    GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE,
)
from app.shared.database import async_session_maker
from app.shared.utils.shared_utils_parsing_utils import (
    parse_iso_datetime as _parse_iso_datetime_value,
)
from app.shared.utils.shared_utils_parsing_utils import (
    parse_positive_int as _parse_positive_int_value,
)

from .shared_jobs_handlers_github_workflow_artifact_parse_payload_handler import (
    build_payload,
    invalid_payload_response,
)
from .shared_jobs_handlers_github_workflow_artifact_parse_persist_handler import (
    persist_artifact_parse_result,
)


def _parse_positive_int(value: Any) -> int | None:
    return _parse_positive_int_value(value)


def _parse_iso_datetime(value: Any) -> datetime | None:
    return _parse_iso_datetime_value(value)


def _normalized_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _build_actions_runner() -> tuple[GithubActionsRunner, GithubClient]:
    github_client = GithubClient(
        base_url=settings.github.GITHUB_API_BASE,
        token=settings.github.GITHUB_TOKEN,
        default_org=settings.github.GITHUB_ORG or None,
    )
    runner = GithubActionsRunner(
        github_client,
        workflow_file=settings.github.GITHUB_ACTIONS_WORKFLOW_FILE,
        poll_interval_seconds=2.0,
        max_poll_seconds=90.0,
    )
    return runner, github_client


async def handle_github_workflow_artifact_parse(
    payload_json: dict[str, Any],
) -> dict[str, Any]:
    """Handle github workflow artifact parse."""
    payload = build_payload(
        payload_json,
        parse_positive_int=_parse_positive_int,
        parse_iso_datetime=_parse_iso_datetime,
        normalized_text=_normalized_text,
    )
    invalid = invalid_payload_response(payload)
    if invalid is not None:
        return invalid
    return await persist_artifact_parse_result(
        async_session_maker=async_session_maker,
        payload=payload,
        build_actions_runner=_build_actions_runner,
        normalized_text=_normalized_text,
    )


__all__ = [
    "GITHUB_WORKFLOW_ARTIFACT_PARSE_JOB_TYPE",
    "handle_github_workflow_artifact_parse",
]
