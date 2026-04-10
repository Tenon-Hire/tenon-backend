from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    serialize_day_windows,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Trial,
)


def build_closed_day_windows(*, now_utc: datetime) -> list[dict[str, datetime | int]]:
    day_windows: list[dict[str, datetime | int]] = []
    for day_index in range(1, 6):
        window_start = now_utc + timedelta(days=day_index)
        window_end = window_start + timedelta(hours=8)
        day_windows.append(
            {
                "dayIndex": day_index,
                "windowStartAt": window_start,
                "windowEndAt": window_end,
            }
        )
    return day_windows


async def set_closed_schedule(async_session, *, candidate_session_id: int) -> None:
    candidate_session = (
        await async_session.execute(
            select(CandidateSession).where(CandidateSession.id == candidate_session_id)
        )
    ).scalar_one()
    _trial = (
        await async_session.execute(
            select(Trial).where(Trial.id == candidate_session.trial_id)
        )
    ).scalar_one()
    now_utc = datetime.now(UTC).replace(microsecond=0)
    day_windows = build_closed_day_windows(now_utc=now_utc)
    candidate_session.scheduled_start_at = day_windows[0]["windowStartAt"]
    candidate_session.candidate_timezone = "UTC"
    candidate_session.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()
