"""TalentPartner update notification jobs and delivery helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailService,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Job,
    Trial,
    User,
    WinoeReport,
)
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.utils.shared_utils_brand_utils import APP_NAME
from app.shared.utils.shared_utils_parsing_utils import parse_positive_int

CANDIDATE_COMPLETED_NOTIFICATION_JOB_TYPE = "candidate_completed_notification"
WINOE_REPORT_READY_NOTIFICATION_JOB_TYPE = "winoe_report_ready_notification"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def build_candidate_completed_notification_idempotency_key(
    candidate_session_id: int,
) -> str:
    """Build the idempotency key for candidate completion notifications."""
    return f"candidate_completed:{int(candidate_session_id)}"


def build_winoe_report_ready_notification_idempotency_key(
    candidate_session_id: int,
) -> str:
    """Build the idempotency key for winoe report ready notifications."""
    return f"winoe_report_ready:{int(candidate_session_id)}"


async def _load_trial_job_context(
    db: AsyncSession, *, trial_id: int
) -> tuple[int, int]:
    row = (
        await db.execute(
            select(Trial.company_id, Trial.created_by).where(Trial.id == trial_id)
        )
    ).one_or_none()
    if row is None:
        raise ValueError("trial_not_found")
    return int(row.company_id), int(row.created_by)


def _build_notification_payload(
    *,
    candidate_session_id: int,
    trial_id: int,
    talent_partner_user_id: int,
) -> dict[str, object]:
    queued_at = _utcnow().isoformat().replace("+00:00", "Z")
    return {
        "candidateSessionId": int(candidate_session_id),
        "trialId": int(trial_id),
        "talentPartnerUserId": int(talent_partner_user_id),
        "queuedAt": queued_at,
    }


async def _enqueue_talent_partner_notification_job(
    db: AsyncSession,
    *,
    job_type: str,
    idempotency_key: str,
    candidate_session_id: int,
    trial_id: int,
    commit: bool,
) -> Job:
    company_id, talent_partner_user_id = await _load_trial_job_context(
        db, trial_id=trial_id
    )
    payload_json = _build_notification_payload(
        candidate_session_id=candidate_session_id,
        trial_id=trial_id,
        talent_partner_user_id=talent_partner_user_id,
    )
    job = await jobs_repo.create_or_get_idempotent(
        db,
        job_type=job_type,
        idempotency_key=idempotency_key,
        payload_json=payload_json,
        company_id=company_id,
        candidate_session_id=candidate_session_id,
        correlation_id=f"candidate_session:{candidate_session_id}:{job_type}",
        commit=False,
    )
    if commit:
        await db.commit()
        await db.refresh(job)
    else:
        await db.flush()
    return job


async def enqueue_candidate_completed_notification(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    trial_id: int,
    commit: bool = True,
) -> Job:
    """Queue a Talent Partner email for completed candidate sessions."""
    return await _enqueue_talent_partner_notification_job(
        db,
        job_type=CANDIDATE_COMPLETED_NOTIFICATION_JOB_TYPE,
        idempotency_key=build_candidate_completed_notification_idempotency_key(
            candidate_session_id
        ),
        candidate_session_id=candidate_session_id,
        trial_id=trial_id,
        commit=commit,
    )


async def enqueue_winoe_report_ready_notification(
    db: AsyncSession,
    *,
    candidate_session_id: int,
    trial_id: int,
    commit: bool = True,
) -> Job:
    """Queue a Talent Partner email when the winoe report becomes ready."""
    return await _enqueue_talent_partner_notification_job(
        db,
        job_type=WINOE_REPORT_READY_NOTIFICATION_JOB_TYPE,
        idempotency_key=build_winoe_report_ready_notification_idempotency_key(
            candidate_session_id
        ),
        candidate_session_id=candidate_session_id,
        trial_id=trial_id,
        commit=commit,
    )


async def _load_talent_partner_notification_row(
    db: AsyncSession, *, candidate_session_id: int
) -> tuple[CandidateSession, Trial, str | None, datetime | None]:
    row = (
        await db.execute(
            select(
                CandidateSession,
                Trial,
                User.email.label("talent_partner_email"),
                WinoeReport.generated_at.label("winoe_report_generated_at"),
            )
            .join(Trial, Trial.id == CandidateSession.trial_id)
            .outerjoin(User, User.id == Trial.created_by)
            .outerjoin(
                WinoeReport, WinoeReport.candidate_session_id == CandidateSession.id
            )
            .where(CandidateSession.id == candidate_session_id)
        )
    ).one_or_none()
    if row is None:
        raise LookupError("candidate_session_not_found")
    return (
        row[0],
        row[1],
        getattr(row, "talent_partner_email", None),
        getattr(row, "winoe_report_generated_at", None),
    )


def _fmt_dt(value: datetime | None) -> str:
    if value is None:
        return "Unavailable"
    normalized = value if value.tzinfo else value.replace(tzinfo=UTC)
    return normalized.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _candidate_identity(candidate_session: CandidateSession) -> tuple[str, str]:
    candidate_name = getattr(candidate_session, "candidate_name", None) or "Candidate"
    candidate_email = (
        getattr(candidate_session, "candidate_email", None)
        or getattr(candidate_session, "invite_email", None)
        or "Unavailable"
    )
    return str(candidate_name), str(candidate_email)


def _candidate_completed_email_content(
    *,
    candidate_name: str,
    candidate_email: str,
    trial: Trial,
    completed_at: datetime | None,
) -> tuple[str, str, str]:
    completed_text = _fmt_dt(completed_at)
    subject = f"Candidate completed: {candidate_name}"
    text = (
        f"{candidate_name} ({candidate_email}) completed all five days of the "
        f"{trial.role} trial in {APP_NAME}.\n\n"
        f"Trial: {trial.title}\n"
        f"Completed at: {completed_text}\n\n"
        "Open the Talent Partner dashboard to review submissions and compare results."
    )
    html = (
        f"<p><strong>{candidate_name}</strong> ({candidate_email}) completed all five"
        f" days of the <strong>{trial.role}</strong> trial in {APP_NAME}.</p>"
        f"<p><strong>Trial:</strong> {trial.title}<br>"
        f"<strong>Completed at:</strong> {completed_text}</p>"
        "<p>Open the Talent Partner dashboard to review submissions and compare results.</p>"
    )
    return subject, text, html


def _winoe_report_ready_email_content(
    *,
    candidate_name: str,
    candidate_email: str,
    trial: Trial,
    generated_at: datetime | None,
) -> tuple[str, str, str]:
    generated_text = _fmt_dt(generated_at)
    subject = f"Winoe Report ready: {candidate_name}"
    text = (
        f"The Winoe Report is ready for {candidate_name} ({candidate_email}).\n\n"
        f"Trial: {trial.title}\n"
        f"Role: {trial.role}\n"
        f"Generated at: {generated_text}\n\n"
        "Open the Talent Partner dashboard to review the final evaluation."
    )
    html = (
        f"<p>The Winoe Report is ready for <strong>{candidate_name}</strong>"
        f" ({candidate_email}).</p>"
        f"<p><strong>Trial:</strong> {trial.title}<br>"
        f"<strong>Role:</strong> {trial.role}<br>"
        f"<strong>Generated at:</strong> {generated_text}</p>"
        "<p>Open the Talent Partner dashboard to review the final evaluation.</p>"
    )
    return subject, text, html


async def _send_talent_partner_update_email(
    *,
    db: AsyncSession,
    candidate_session_id: int,
    email_service: EmailService,
    mode: str,
) -> dict[str, Any]:
    (
        candidate_session,
        trial,
        talent_partner_email,
        winoe_report_generated_at,
    ) = await _load_talent_partner_notification_row(
        db, candidate_session_id=candidate_session_id
    )
    if not talent_partner_email or not talent_partner_email.strip():
        return {"status": "skipped", "reason": "missing_talent_partner_email"}

    candidate_name, candidate_email = _candidate_identity(candidate_session)
    if mode == "candidate_completed":
        subject, text, html = _candidate_completed_email_content(
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            trial=trial,
            completed_at=getattr(candidate_session, "completed_at", None),
        )
    else:
        subject, text, html = _winoe_report_ready_email_content(
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            trial=trial,
            generated_at=winoe_report_generated_at,
        )

    result = await email_service.send_email(
        to=talent_partner_email,
        subject=subject,
        text=text,
        html=html,
    )
    if result.status != "sent":
        raise RuntimeError(result.error or "talent_partner_notification_send_failed")
    return {
        "status": "sent",
        "candidateSessionId": candidate_session_id,
        "to": talent_partner_email,
        "messageId": result.message_id,
        "mode": mode,
    }


def _parse_candidate_session_id(payload_json: dict[str, Any]) -> int:
    candidate_session_id = parse_positive_int(payload_json.get("candidateSessionId"))
    if candidate_session_id is None:
        raise ValueError("candidateSessionId is required")
    return candidate_session_id


async def process_candidate_completed_notification_job(
    payload_json: dict[str, Any],
    *,
    async_session_maker_obj: async_sessionmaker[AsyncSession],
    email_service: EmailService,
) -> dict[str, Any]:
    """Send the Talent Partner email for a completed candidate session."""
    candidate_session_id = _parse_candidate_session_id(payload_json)
    async with async_session_maker_obj() as db:
        return await _send_talent_partner_update_email(
            db=db,
            candidate_session_id=candidate_session_id,
            email_service=email_service,
            mode="candidate_completed",
        )


async def process_winoe_report_ready_notification_job(
    payload_json: dict[str, Any],
    *,
    async_session_maker_obj: async_sessionmaker[AsyncSession],
    email_service: EmailService,
) -> dict[str, Any]:
    """Send the Talent Partner email for a ready winoe report."""
    candidate_session_id = _parse_candidate_session_id(payload_json)
    async with async_session_maker_obj() as db:
        return await _send_talent_partner_update_email(
            db=db,
            candidate_session_id=candidate_session_id,
            email_service=email_service,
            mode="winoe_report_ready",
        )


__all__ = [
    "CANDIDATE_COMPLETED_NOTIFICATION_JOB_TYPE",
    "WINOE_REPORT_READY_NOTIFICATION_JOB_TYPE",
    "build_candidate_completed_notification_idempotency_key",
    "build_winoe_report_ready_notification_idempotency_key",
    "enqueue_candidate_completed_notification",
    "enqueue_winoe_report_ready_notification",
    "process_candidate_completed_notification_job",
    "process_winoe_report_ready_notification_job",
]
