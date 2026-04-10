from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    derive_day_windows,
    serialize_day_windows,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Trial,
)
from app.shared.jobs import worker


async def _create_trial(async_client, async_session, talent_partner_email: str) -> int:
    payload = {
        "title": "Backend Node Trial",
        "role": "Backend Engineer",
        "techStack": "Node.js, PostgreSQL",
        "seniority": "Mid",
        "focus": "Build new API feature and debug an issue",
    }
    res = await async_client.post(
        "/api/trials",
        json=payload,
        headers={"x-dev-user-email": talent_partner_email},
    )
    assert res.status_code in (200, 201), res.text
    sim_id = res.json()["id"]
    session_maker = async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )
    worker.clear_handlers()
    try:
        worker.register_builtin_handlers()
        handled = await worker.run_once(
            session_maker=session_maker,
            worker_id="candidate-session-resolve-worker",
            now=datetime.now(UTC),
        )
    finally:
        worker.clear_handlers()
    assert handled is True
    activate = await async_client.post(
        f"/api/trials/{sim_id}/activate",
        json={"confirm": True},
        headers={"x-dev-user-email": talent_partner_email},
    )
    assert activate.status_code == 200, activate.text
    return sim_id


async def _apply_schedule(
    async_session,
    *,
    candidate_session_id: int,
    scheduled_start_at: datetime,
    candidate_timezone: str,
) -> None:
    cs = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == candidate_session_id)
        )
    ).scalar_one()
    sim = (
        await async_session.execute(select(Trial).where(Trial.id == cs.trial_id))
    ).scalar_one()
    day_windows = derive_day_windows(
        scheduled_start_at_utc=scheduled_start_at,
        candidate_tz=candidate_timezone,
        day_window_start_local=sim.day_window_start_local,
        day_window_end_local=sim.day_window_end_local,
        overrides=sim.day_window_overrides_json,
        overrides_enabled=bool(sim.day_window_overrides_enabled),
        total_days=5,
    )
    cs.scheduled_start_at = scheduled_start_at
    cs.candidate_timezone = candidate_timezone
    cs.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()
