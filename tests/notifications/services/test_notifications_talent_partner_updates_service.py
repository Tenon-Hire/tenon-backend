from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailSendResult,
)
from app.notifications.services.notifications_services_notifications_talent_partner_updates_service import (
    build_candidate_completed_notification_idempotency_key,
    build_winoe_report_ready_notification_idempotency_key,
    enqueue_candidate_completed_notification,
    enqueue_winoe_report_ready_notification,
    process_candidate_completed_notification_job,
    process_winoe_report_ready_notification_job,
)
from app.shared.database.shared_database_models_model import WinoeReport
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


def _session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind,
        expire_on_commit=False,
        autoflush=False,
    )


class _RecorderEmailService:
    def __init__(self):
        self.calls: list[dict[str, str | None]] = []

    async def send_email(self, *, to: str, subject: str, text: str, html: str | None):
        self.calls.append({"to": to, "subject": subject, "text": text, "html": html})
        return EmailSendResult(status="sent", message_id="msg-123")


@pytest.mark.asyncio
async def test_enqueue_talent_partner_update_jobs_are_idempotent(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="notify-jobs@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="completed",
        completed_at=datetime.now(UTC),
        candidate_email="candidate@example.com",
    )
    await async_session.commit()

    first_completed = await enqueue_candidate_completed_notification(
        async_session,
        candidate_session_id=candidate_session.id,
        trial_id=trial.id,
        commit=True,
    )
    second_completed = await enqueue_candidate_completed_notification(
        async_session,
        candidate_session_id=candidate_session.id,
        trial_id=trial.id,
        commit=True,
    )
    first_fit = await enqueue_winoe_report_ready_notification(
        async_session,
        candidate_session_id=candidate_session.id,
        trial_id=trial.id,
        commit=True,
    )
    second_fit = await enqueue_winoe_report_ready_notification(
        async_session,
        candidate_session_id=candidate_session.id,
        trial_id=trial.id,
        commit=True,
    )

    assert first_completed.id == second_completed.id
    assert first_completed.idempotency_key == (
        build_candidate_completed_notification_idempotency_key(candidate_session.id)
    )
    assert first_fit.id == second_fit.id
    assert first_fit.idempotency_key == (
        build_winoe_report_ready_notification_idempotency_key(candidate_session.id)
    )


@pytest.mark.asyncio
async def test_process_talent_partner_update_jobs_send_expected_email(async_session):
    talent_partner_email = f"notify-send-talent_partner-{uuid4().hex}@test.com"
    talent_partner = await create_talent_partner(
        async_session, email=talent_partner_email
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="completed",
        completed_at=datetime.now(UTC),
        candidate_email="candidate@example.com",
    )
    async_session.add(
        WinoeReport(
            candidate_session_id=candidate_session.id,
            generated_at=datetime.now(UTC),
        )
    )
    await async_session.commit()

    session_maker = _session_maker(async_session)

    email_service = _RecorderEmailService()
    completed_result = await process_candidate_completed_notification_job(
        {"candidateSessionId": candidate_session.id},
        async_session_maker_obj=session_maker,
        email_service=email_service,
    )
    fit_result = await process_winoe_report_ready_notification_job(
        {"candidateSessionId": candidate_session.id},
        async_session_maker_obj=session_maker,
        email_service=email_service,
    )

    assert completed_result["status"] == "sent"
    assert fit_result["status"] == "sent"
    assert len(email_service.calls) == 2
    assert email_service.calls[0]["to"] == talent_partner_email
    assert "completed all five days" in (email_service.calls[0]["text"] or "")
    assert "Winoe Report is ready" in (email_service.calls[1]["text"] or "")
