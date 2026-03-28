"""Application module for notifications services notifications schedule content service workflows."""

from __future__ import annotations

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from app.shared.utils.shared_utils_brand_utils import APP_NAME


def _fmt_local_window(start_local: time, end_local: time) -> str:
    return f"{start_local.strftime('%H:%M')} - {end_local.strftime('%H:%M')}"


def _fmt_start_local(start_at_utc: datetime, timezone_name: str) -> str:
    local_start = start_at_utc.astimezone(ZoneInfo(timezone_name))
    return local_start.strftime("%Y-%m-%d %H:%M %Z")


def candidate_schedule_confirmation_content(
    *,
    candidate_name: str,
    simulation_title: str,
    role: str,
    scheduled_start_at_utc: datetime,
    timezone_name: str,
    day_window_start_local: time,
    day_window_end_local: time,
) -> tuple[str, str, str]:
    """Execute candidate schedule confirmation content."""
    start_utc = (
        scheduled_start_at_utc.replace(tzinfo=UTC)
        if scheduled_start_at_utc.tzinfo is None
        else scheduled_start_at_utc.astimezone(UTC)
    )
    start_local_text = _fmt_start_local(start_utc, timezone_name)
    window_text = _fmt_local_window(day_window_start_local, day_window_end_local)
    subject = f"Schedule confirmed: {simulation_title}"
    text = (
        f"Hi {candidate_name},\n\n"
        f"Your schedule for the {role} simulation in {APP_NAME} is confirmed.\n"
        f"Simulation: {simulation_title}\n"
        f"Start: {start_local_text} ({timezone_name})\n"
        f"Daily window: {window_text} ({timezone_name})\n\n"
        "Your schedule is now locked."
    )
    html = (
        f"<p>Hi {candidate_name},</p>"
        f"<p>Your schedule for the <strong>{role}</strong> simulation in {APP_NAME} is confirmed.</p>"
        f"<p><strong>Simulation:</strong> {simulation_title}<br>"
        f"<strong>Start:</strong> {start_local_text} ({timezone_name})<br>"
        f"<strong>Daily window:</strong> {window_text} ({timezone_name})</p>"
        "<p>Your schedule is now locked.</p>"
    )
    return subject, text, html


def recruiter_schedule_confirmation_content(
    *,
    candidate_name: str,
    candidate_email: str,
    simulation_title: str,
    role: str,
    scheduled_start_at_utc: datetime,
    timezone_name: str,
    day_window_start_local: time,
    day_window_end_local: time,
) -> tuple[str, str, str]:
    """Execute recruiter schedule confirmation content."""
    start_utc = (
        scheduled_start_at_utc.replace(tzinfo=UTC)
        if scheduled_start_at_utc.tzinfo is None
        else scheduled_start_at_utc.astimezone(UTC)
    )
    start_local_text = _fmt_start_local(start_utc, timezone_name)
    window_text = _fmt_local_window(day_window_start_local, day_window_end_local)
    subject = f"Candidate scheduled: {candidate_name}"
    text = (
        f"Candidate {candidate_name} ({candidate_email}) confirmed their schedule.\n\n"
        f"Simulation: {simulation_title}\n"
        f"Role: {role}\n"
        f"Start: {start_local_text} ({timezone_name})\n"
        f"Daily window: {window_text} ({timezone_name})\n"
    )
    html = (
        f"<p>Candidate <strong>{candidate_name}</strong> ({candidate_email}) confirmed their schedule.</p>"
        f"<p><strong>Simulation:</strong> {simulation_title}<br>"
        f"<strong>Role:</strong> {role}<br>"
        f"<strong>Start:</strong> {start_local_text} ({timezone_name})<br>"
        f"<strong>Daily window:</strong> {window_text} ({timezone_name})</p>"
    )
    return subject, text, html


__all__ = [
    "candidate_schedule_confirmation_content",
    "recruiter_schedule_confirmation_content",
]
