"""Application module for notifications services notifications invite content service workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from app.shared.database.shared_database_models_model import Trial
from app.shared.utils.shared_utils_brand_utils import APP_NAME


def sanitize_error(err: str | None) -> str | None:
    """Sanitize error."""
    return err[:200] if err else None


def invite_email_content(
    *,
    candidate_name: str,
    invite_url: str,
    trial: Trial,
    expires_at: datetime | None,
) -> tuple[str, str, str]:
    """Execute invite email content."""
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    expires_text = (
        expires_at.astimezone(UTC).strftime("%Y-%m-%d") if expires_at else "soon"
    )
    subject = f"You're invited: {trial.title}"
    text = (
        f"Hi {candidate_name},\n\n"
        f"You've been invited to complete the {trial.role} trial in {APP_NAME}.\n"
        f"Trial: {trial.title}\n"
        f"Role: {trial.role}\n\n"
        f"Start here: {invite_url}\n\n"
        f"Your invite expires on {expires_text}. "
        "If you did not expect this email, you can ignore it."
    )
    html = (
        f"<p>Hi {candidate_name},</p>"
        f"<p>You have been invited to complete the <strong>{trial.role}</strong> trial in {APP_NAME}.</p>"
        f"<p><strong>Trial:</strong> {trial.title}<br>"
        f"<strong>Role:</strong> {trial.role}</p>"
        f'<p><a href="{invite_url}">Open your invite</a></p>'
        f"<p>This invite expires on {expires_text}.</p>"
    )
    return subject, text, html
