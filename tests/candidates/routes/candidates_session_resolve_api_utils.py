# helper import baseline for restructure-compat
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Company,
    Submission,
    Task,
    User,
)
from tests.candidates.routes.candidates_session_resolve_flow_api_utils import (
    _apply_schedule,
    _create_trial,
)


async def _seed_talent_partner(
    async_session, email: str = "talent_partner1@winoe.com"
) -> User:
    company = Company(name="TestCo")
    async_session.add(company)
    await async_session.commit()
    await async_session.refresh(company)

    user = User(
        name="TalentPartner One",
        email=email,
        role="talent_partner",
        company_id=company.id,
        password_hash="",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


async def _invite_candidate(
    async_client,
    sim_id: int,
    talent_partner_email: str,
    invite_email: str = "jane@example.com",
) -> dict:
    payload = {"candidateName": "Jane Doe", "inviteEmail": invite_email}
    res = await async_client.post(
        f"/api/trials/{sim_id}/invite",
        json=payload,
        headers={"x-dev-user-email": talent_partner_email},
    )
    assert res.status_code == 200, res.text
    return res.json()


async def _claim(async_client, token: str, email: str) -> dict:
    res = await async_client.get(
        f"/api/candidate/session/{token}",
        headers={"Authorization": f"Bearer candidate:{email}"},
    )
    assert res.status_code == 200, res.text
    return res.json()


def _next_local_window_start_utc(
    timezone_name: str, *, days_ahead: int = 1
) -> datetime:
    zone = ZoneInfo(timezone_name)
    local_date = datetime.now(UTC).astimezone(zone).date() + timedelta(days=days_ahead)
    local_start = datetime.combine(local_date, time(hour=9, minute=0), tzinfo=zone)
    return local_start.astimezone(UTC).replace(microsecond=0)


__all__ = [name for name in globals() if not name.startswith("__")]
