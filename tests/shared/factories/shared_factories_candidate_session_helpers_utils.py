from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import build_ai_policy_snapshot
from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    serialize_day_windows,
)
from app.shared.database.shared_database_models_model import ScenarioVersion, Trial


def _resolve_schedule_defaults(
    *,
    with_default_schedule: bool,
    scheduled_start_at: datetime | None,
    candidate_timezone: str | None,
    day_windows_json: list[dict] | None,
) -> tuple[datetime | None, str | None, list[dict] | None]:
    resolved_scheduled_start = scheduled_start_at
    resolved_timezone = candidate_timezone
    resolved_day_windows = day_windows_json
    if (
        with_default_schedule
        and resolved_scheduled_start is None
        and resolved_day_windows is None
    ):
        now_utc = datetime.now(UTC).replace(microsecond=0)
        resolved_scheduled_start = now_utc - timedelta(days=1)
        resolved_timezone = resolved_timezone or "UTC"
        open_window_start = now_utc - timedelta(days=1)
        open_window_end = now_utc + timedelta(days=1)
        resolved_day_windows = serialize_day_windows(
            [
                {
                    "dayIndex": day_index,
                    "windowStartAt": open_window_start,
                    "windowEndAt": open_window_end,
                }
                for day_index in range(1, 6)
            ]
        )
    return resolved_scheduled_start, resolved_timezone, resolved_day_windows


async def _resolve_candidate_session_scenario_version_id(
    session: AsyncSession,
    *,
    trial: Trial,
    scenario_version_id: int | None,
) -> int:
    resolved = scenario_version_id or trial.active_scenario_version_id
    if resolved is not None:
        return resolved
    existing = (
        await session.execute(
            select(ScenarioVersion)
            .where(ScenarioVersion.trial_id == trial.id)
            .order_by(ScenarioVersion.version_index.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = ScenarioVersion(
            trial_id=trial.id,
            version_index=1,
            status="ready",
            storyline_md=f"# {trial.title}",
            task_prompts_json=[],
            rubric_json={},
            focus_notes=trial.focus or "",
            template_key=trial.template_key,
            tech_stack=trial.tech_stack,
            seniority=trial.seniority,
            ai_policy_snapshot_json=build_ai_policy_snapshot(trial=trial),
        )
        session.add(existing)
        await session.flush()
    trial.active_scenario_version_id = existing.id
    await session.flush()
    return existing.id
