from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    serialize_day_windows,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    Submission,
    Trial,
    Workspace,
)
from tests.shared.factories import (
    create_candidate_session,
    create_submission,
    create_talent_partner,
)
from tests.shared.factories import (
    create_trial as create_trial_factory,
)
from tests.tasks.routes.test_tasks_submit_api_flow_utils import (
    claim_session,
    get_current_task,
    invite_candidate,
    seed_talent_partner,
)
from tests.tasks.routes.test_tasks_submit_api_runtime_utils import (
    create_trial as create_trial_runtime,
)

create_trial = create_trial_runtime


async def unlock_schedule(
    async_session: AsyncSession,
    *,
    candidate_session_id: int,
    timezone_name: str = "America/New_York",
) -> None:
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
    open_window_start = now_utc - timedelta(days=1)
    open_window_end = now_utc + timedelta(days=1)
    scheduled_start = open_window_start
    day_windows = [
        {
            "dayIndex": day_index,
            "windowStartAt": open_window_start,
            "windowEndAt": open_window_end,
        }
        for day_index in range(1, 6)
    ]
    candidate_session.scheduled_start_at = scheduled_start
    candidate_session.candidate_timezone = timezone_name
    candidate_session.day_windows_json = serialize_day_windows(day_windows)
    await async_session.commit()


def candidate_headers(cs_id: int, token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "x-candidate-session-id": str(cs_id),
    }


def task_id_by_day(sim_json: dict, day_index: int) -> int:
    # create_trial returns tasks with snake_case keys (day_index/type/etc)
    for t in sim_json["tasks"]:
        if t["day_index"] == day_index:
            return t["id"]
    raise AssertionError(f"Trial missing task for day_index={day_index}")


def build_day5_reflection_payload() -> dict:
    return {
        "reflection": {
            "challenges": (
                "I managed conflicting constraints by listing assumptions and "
                "validating them early."
            ),
            "decisions": (
                "I favored explicit schema validation so frontend error handling "
                "remains deterministic."
            ),
            "tradeoffs": (
                "I chose stricter section requirements over flexibility to improve "
                "rubric scoring consistency."
            ),
            "communication": (
                "I wrote clear handoff notes describing open questions and known "
                "limitations for evaluators."
            ),
            "next": (
                "Next I would add evaluator evidence linking and richer rubric "
                "mapping for section scoring."
            ),
        },
        "contentText": (
            "## Challenges\n...\n## Decisions\n...\n## Tradeoffs\n...\n"
            "## Communication / Handoff\n...\n## What I'd do next\n..."
        ),
    }


__all__ = [name for name in globals() if not name.startswith("__")]
