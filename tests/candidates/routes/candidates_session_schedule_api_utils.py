from __future__ import annotations

# helper import baseline for restructure-compat
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.api.main import app
from app.integrations.email.email_provider import MemoryEmailProvider
from app.notifications.services.notifications_services_notifications_email_sender_service import (
    EmailService,
)
from app.shared.database.shared_database_models_model import CandidateSession
from app.shared.http.dependencies.shared_http_dependencies_notifications_utils import (
    get_email_service,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


def _next_local_window_start_utc(
    timezone_name: str, *, days_ahead: int = 1
) -> datetime:
    zone = ZoneInfo(timezone_name)
    local_date = datetime.now(UTC).astimezone(zone).date() + timedelta(days=days_ahead)
    local_start = datetime.combine(local_date, time(hour=9, minute=0), tzinfo=zone)
    return local_start.astimezone(UTC)


async def _seed_claimed_session(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="schedule-talent_partner@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="schedule-candidate@test.com",
    )
    await async_session.commit()
    return talent_partner, trial, candidate_session


async def _claim(async_client, token: str, email: str):
    response = await async_client.post(
        f"/api/candidate/session/{token}/claim",
        headers={"Authorization": f"Bearer candidate:{email}"},
    )
    assert response.status_code == 200, response.text


__all__ = [name for name in globals() if not name.startswith("__")]
