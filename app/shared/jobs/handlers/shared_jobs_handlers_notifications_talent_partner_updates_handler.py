"""Worker handlers for Talent Partner update notification emails."""

from __future__ import annotations

from typing import Any

from app.notifications.services.notifications_services_notifications_talent_partner_updates_service import (
    CANDIDATE_COMPLETED_NOTIFICATION_JOB_TYPE,
    WINOE_REPORT_READY_NOTIFICATION_JOB_TYPE,
    process_candidate_completed_notification_job,
    process_winoe_report_ready_notification_job,
)
from app.shared.database import async_session_maker
from app.shared.http.dependencies.shared_http_dependencies_notifications_utils import (
    get_email_service,
)
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_types_model import (
    PermanentJobError,
)


async def handle_candidate_completed_notification(
    payload_json: dict[str, Any],
) -> dict[str, Any]:
    """Handle Talent Partner candidate completed notification jobs."""
    try:
        return await process_candidate_completed_notification_job(
            payload_json,
            async_session_maker_obj=async_session_maker,
            email_service=get_email_service(),
        )
    except ValueError as exc:
        raise PermanentJobError(str(exc)) from exc


async def handle_winoe_report_ready_notification(
    payload_json: dict[str, Any],
) -> dict[str, Any]:
    """Handle Talent Partner winoe report ready notification jobs."""
    try:
        return await process_winoe_report_ready_notification_job(
            payload_json,
            async_session_maker_obj=async_session_maker,
            email_service=get_email_service(),
        )
    except ValueError as exc:
        raise PermanentJobError(str(exc)) from exc


__all__ = [
    "CANDIDATE_COMPLETED_NOTIFICATION_JOB_TYPE",
    "WINOE_REPORT_READY_NOTIFICATION_JOB_TYPE",
    "handle_candidate_completed_notification",
    "handle_winoe_report_ready_notification",
]
